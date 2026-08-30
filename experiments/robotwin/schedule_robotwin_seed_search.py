"""Run command jobs through a persistent SQLite GPU FIFO queue."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEARCH_ENTRY = PROJECT_ROOT / "experiments" / "robotwin" / "search_robotwin_seeds.py"
DEFAULT_CHECKPOINT = "checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt"
LEGACY_SEARCH_DATABASE = "evaluate_results/robotwin/seed_search/scheduler.sqlite3"
JOB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class SchedulerTerminated(Exception):
    pass


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_csv(raw: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("Expected a non-empty comma-separated value list.")
    return values


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _parse_gpu_ids(raw: str) -> list[str]:
    values = _parse_csv(raw)
    if any(not value.isdecimal() for value in values):
        raise ValueError("--gpu-ids must contain non-negative integer GPU indices.")
    gpu_ids = [str(int(value)) for value in values]
    if len(gpu_ids) != len(set(gpu_ids)):
        raise ValueError("--gpu-ids must not contain duplicate physical GPU indices.")
    return gpu_ids


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS experiments (
            name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            config_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            experiment_name TEXT NOT NULL REFERENCES experiments(name),
            task_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'completed', 'failed', 'timed_out', 'cancelled')),
            gpu_id TEXT,
            started_at TEXT,
            finished_at TEXT,
            exit_code INTEGER,
            output_dir TEXT NOT NULL,
            command_json TEXT,
            error_text TEXT,
            UNIQUE(experiment_name, task_name)
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            job_id INTEGER REFERENCES jobs(id),
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL
        );
        """
    )
    return connection


def _event(connection: sqlite3.Connection, log_file: Path, job_id: int | None, event_type: str, message: str) -> None:
    timestamp = _now()
    connection.execute(
        "INSERT INTO events(job_id, timestamp, event_type, message) VALUES (?, ?, ?, ?)",
        (job_id, timestamp, event_type, message),
    )
    connection.commit()
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {event_type} {message}\n")


def _validate_job_name(name: Any) -> str:
    if not isinstance(name, str) or not JOB_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid job name {name!r}; use letters, digits, dots, underscores, or hyphens.")
    return name


def _validate_argv(argv: Any, label: str) -> list[str]:
    if not isinstance(argv, list) or not argv or any(not isinstance(part, str) or not part for part in argv):
        raise ValueError(f"{label} must be a non-empty argv string list.")
    if Path(argv[0]).name != "uv" or len(argv) < 2 or argv[1] != "run":
        raise ValueError(f"{label} must begin with `uv run`.")
    return list(argv)


def _load_command_jobs(raw_path: str) -> list[dict[str, Any]]:
    path = _resolve_path(raw_path)
    if not path.is_file():
        raise FileNotFoundError(f"Jobs file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Jobs file must contain a JSON mapping.")
    default_argv = payload.get("argv_template")
    if default_argv is not None:
        default_argv = _validate_argv(default_argv, "argv_template")
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise ValueError("Jobs file must contain a non-empty jobs list.")

    jobs: list[dict[str, Any]] = []
    for index, raw_job in enumerate(raw_jobs):
        if isinstance(raw_job, str):
            name = _validate_job_name(raw_job)
            argv = default_argv
        elif isinstance(raw_job, dict):
            name = _validate_job_name(raw_job.get("name"))
            argv = raw_job.get("argv", default_argv)
        else:
            raise ValueError(f"jobs[{index}] must be a job name or JSON mapping.")
        if argv is None:
            raise ValueError(f"jobs[{index}] must define argv or use a top-level argv_template.")
        jobs.append({"name": name, "argv": _validate_argv(argv, f"jobs[{index}].argv")})
    names = [job["name"] for job in jobs]
    if len(names) != len(set(names)):
        raise ValueError("Jobs file must not contain duplicate job names.")
    return jobs


def _render_argv(argv: list[str], job_name: str, gpu_id: str, output_dir: Path) -> list[str]:
    replacements = {
        "{gpu_id}": gpu_id,
        "{job_name}": job_name,
        "{output_dir}": str(output_dir),
    }
    return [
        part.replace("{gpu_id}", replacements["{gpu_id}"])
        .replace("{job_name}", replacements["{job_name}"])
        .replace("{output_dir}", replacements["{output_dir}"])
        for part in argv
    ]


def _command(
    args: argparse.Namespace,
    job_name: str,
    gpu_id: str,
    output_dir: Path,
    command_jobs: dict[str, list[str]],
) -> list[str]:
    if command_jobs:
        return _render_argv(command_jobs[job_name], job_name, gpu_id, output_dir)

    command = [
        "uv",
        "run",
        "--no-sync",
        "python",
        str(SEARCH_ENTRY),
        "--task-name",
        job_name,
        "--phases",
        "clean,random",
        "--gpu-ids",
        gpu_id,
        "--seed",
        str(args.seed),
    ]
    if args.environment_seed_start is not None:
        command.extend([
            "--environment-seed-start",
            str(args.environment_seed_start),
        ])
    command.extend([
        "--max-seed-attempts",
        str(args.max_seed_attempts),
        "--target-good-seeds",
        str(args.target_good_seeds),
        "--repeats",
        str(args.repeats),
        "--ckpt",
        args.ckpt,
        "--output-dir",
        str(output_dir),
    ])
    if args.dataset_stats_path:
        command.extend(["--dataset-stats-path", args.dataset_stats_path])
    return command


def _terminate(process: subprocess.Popen[Any]) -> None:
    process_group = process.pid
    try:
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        process.poll()
        try:
            os.killpg(process_group, 0)
        except ProcessLookupError:
            process.wait()
            return
        time.sleep(0.1)

    try:
        os.killpg(process_group, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _handle_sigterm(_signum: int, _frame: Any) -> None:
    raise SchedulerTerminated("scheduler received SIGTERM")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-name", required=True, help="Name of the matching docs/experiments directory.")
    jobs = parser.add_mutually_exclusive_group(required=True)
    jobs.add_argument(
        "--jobs-file",
        help=(
            "JSON command jobs; argv may use {gpu_id}, {job_name}, and {output_dir}. "
            "With a top-level argv_template, jobs may be a list of names."
        ),
    )
    jobs.add_argument("--task-names", help="Legacy comma-separated RoboTwin seed-search task names.")
    parser.add_argument("--gpu-ids", required=True, help="Comma-separated physical GPU ids.")
    parser.add_argument("--max-tasks-per-gpu", type=int, default=2)
    parser.add_argument("--task-timeout-seconds", type=int, default=10 * 60 * 60)
    parser.add_argument("--poll-interval-seconds", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--environment-seed-start", type=int, default=None)
    parser.add_argument("--max-seed-attempts", type=int, default=1000)
    parser.add_argument("--target-good-seeds", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--ckpt", default=DEFAULT_CHECKPOINT)
    parser.add_argument("--dataset-stats-path", default=None)
    parser.add_argument(
        "--database",
        default=None,
        help=(
            "Persistent SQLite queue database (default with --jobs-file: <output-dir>/scheduler.sqlite3; "
            f"legacy --task-names calls use {LEGACY_SEARCH_DATABASE})."
        ),
    )
    parser.add_argument("--output-dir", required=True, help="New result root for this scheduler run.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    job_specs = _load_command_jobs(args.jobs_file) if args.jobs_file else []
    jobs = [job["name"] for job in job_specs] if job_specs else _parse_csv(args.task_names)
    command_jobs = {job["name"]: job["argv"] for job in job_specs}
    gpu_ids = _parse_gpu_ids(args.gpu_ids)
    if not job_specs:
        jobs = [_validate_job_name(job_name) for job_name in jobs]
    if len(jobs) != len(set(jobs)):
        raise ValueError("Job names must not contain duplicates.")
    if args.max_tasks_per_gpu <= 0 or args.task_timeout_seconds <= 0 or args.poll_interval_seconds <= 0:
        raise ValueError("Capacity, timeout, and poll interval must be positive.")

    output_root = _resolve_path(args.output_dir)
    if args.database:
        database_path = _resolve_path(args.database)
    elif args.task_names:
        database_path = _resolve_path(LEGACY_SEARCH_DATABASE)
    else:
        database_path = output_root / "scheduler.sqlite3"
    if output_root.exists():
        raise FileExistsError(f"Output directory already exists: {output_root}")
    output_root.mkdir(parents=True)
    launcher_logs = output_root / "launcher_logs"
    launcher_logs.mkdir()
    scheduler_log = output_root / "scheduler.log"
    run_config = vars(args) | {
        "database": str(database_path),
        "job_names": jobs,
        "command_jobs": job_specs,
        "gpu_ids": gpu_ids,
        "created_at": _now(),
    }
    if not job_specs:
        run_config["task_names"] = jobs
    (output_root / "scheduler-run-config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    connection = _connect(database_path)
    existing = connection.execute("SELECT 1 FROM experiments WHERE name = ?", (args.experiment_name,)).fetchone()
    if existing:
        connection.close()
        raise ValueError(f"Experiment already exists in SQLite queue: {args.experiment_name}")
    connection.execute(
        "INSERT INTO experiments(name, created_at, config_json) VALUES (?, ?, ?)",
        (args.experiment_name, _now(), json.dumps(run_config, ensure_ascii=False)),
    )
    job_output_root = output_root / "jobs" if command_jobs else output_root
    if command_jobs:
        job_output_root.mkdir()
    for job_name in jobs:
        connection.execute(
            "INSERT INTO jobs(experiment_name, task_name, status, output_dir, command_json) "
            "VALUES (?, ?, 'queued', ?, ?)",
            (
                args.experiment_name,
                job_name,
                str(job_output_root / job_name),
                json.dumps(command_jobs[job_name]) if command_jobs else None,
            ),
        )
    connection.commit()
    _event(connection, scheduler_log, None, "scheduler_started", f"experiment={args.experiment_name} jobs={','.join(jobs)}")
    if args.dry_run:
        _event(connection, scheduler_log, None, "dry_run", "jobs queued without launching subprocesses")
        connection.close()
        return

    running: dict[int, tuple[subprocess.Popen[Any], float, str, str]] = {}
    slots = [gpu_id for _ in range(args.max_tasks_per_gpu) for gpu_id in gpu_ids]
    previous_sigterm_handler = signal.signal(signal.SIGTERM, _handle_sigterm)
    try:
        while True:
            for job_id, (process, started, job_name, gpu_id) in list(running.items()):
                return_code = process.poll()
                elapsed = time.monotonic() - started
                if return_code is None and elapsed < args.task_timeout_seconds:
                    continue
                if return_code is None:
                    _terminate(process)
                    connection.execute(
                        "UPDATE jobs SET status='timed_out', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                        (_now(), process.returncode, f"job exceeded {args.task_timeout_seconds} seconds", job_id),
                    )
                    _event(connection, scheduler_log, job_id, "timed_out", f"job={job_name} gpu={gpu_id}")
                else:
                    _terminate(process)
                if return_code == 0:
                    connection.execute(
                        "UPDATE jobs SET status='completed', finished_at=?, exit_code=? WHERE id=?",
                        (_now(), return_code, job_id),
                    )
                    _event(connection, scheduler_log, job_id, "completed", f"job={job_name} gpu={gpu_id}")
                elif return_code is not None:
                    connection.execute(
                        "UPDATE jobs SET status='failed', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                        (_now(), return_code, f"subprocess exited with {return_code}", job_id),
                    )
                    _event(connection, scheduler_log, job_id, "failed", f"job={job_name} gpu={gpu_id} exit_code={return_code}")
                del running[job_id]

            used = [gpu_id for _, _, _, gpu_id in running.values()]
            for gpu_id in slots:
                if used.count(gpu_id) >= args.max_tasks_per_gpu:
                    continue
                row = connection.execute(
                    "SELECT id, task_name, output_dir FROM jobs WHERE experiment_name=? AND status='queued' ORDER BY id LIMIT 1",
                    (args.experiment_name,),
                ).fetchone()
                if row is None:
                    break
                task_output = Path(row["output_dir"])
                job_name = str(row["task_name"])
                command = _command(args, job_name, gpu_id, task_output, command_jobs)
                environment = os.environ.copy()
                environment["CUDA_VISIBLE_DEVICES"] = gpu_id
                environment["ROBOTWIN_SCHEDULER_GPU_ID"] = gpu_id
                environment["ROBOTWIN_SCHEDULER_OUTPUT_DIR"] = str(task_output)
                with (launcher_logs / f"{row['task_name']}.log").open("w", encoding="utf-8") as log_handle:
                    process = subprocess.Popen(
                        command,
                        cwd=PROJECT_ROOT,
                        env=environment,
                        stdout=log_handle,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                running[int(row["id"])] = (process, time.monotonic(), job_name, gpu_id)
                connection.execute(
                    "UPDATE jobs SET status='running', gpu_id=?, started_at=?, command_json=? WHERE id=?",
                    (gpu_id, _now(), json.dumps(command), row["id"]),
                )
                _event(connection, scheduler_log, int(row["id"]), "started", f"job={job_name} gpu={gpu_id} pid={process.pid}")
                used.append(gpu_id)

            queued = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE experiment_name=? AND status='queued'", (args.experiment_name,)
            ).fetchone()[0]
            if not running and queued == 0:
                break
            time.sleep(args.poll_interval_seconds)
    except BaseException as error:
        interrupted = isinstance(error, (KeyboardInterrupt, SchedulerTerminated))
        reason = "scheduler interrupted" if interrupted else f"scheduler failed: {error}"
        for job_id, (process, _, job_name, _) in running.items():
            job_reason = reason
            try:
                _terminate(process)
            except Exception as cleanup_error:
                job_reason = f"{reason}; process cleanup failed: {cleanup_error}"
            try:
                connection.execute(
                    "UPDATE jobs SET status='cancelled', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                    (_now(), process.returncode, job_reason, job_id),
                )
                _event(connection, scheduler_log, job_id, "cancelled", f"job={job_name} reason={job_reason}")
            except Exception:
                pass
        try:
            connection.execute(
                "UPDATE jobs SET status='cancelled', finished_at=?, error_text=? "
                "WHERE experiment_name=? AND status='queued'",
                (_now(), reason, args.experiment_name),
            )
            _event(connection, scheduler_log, None, "scheduler_cancelled", f"reason={reason}")
        except Exception:
            pass
        if isinstance(error, SchedulerTerminated):
            return
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm_handler)
        connection.close()


if __name__ == "__main__":
    main()
