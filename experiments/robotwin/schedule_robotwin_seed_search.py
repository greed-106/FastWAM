"""Run RoboTwin seed-search tasks through a persistent SQLite FIFO queue."""

from __future__ import annotations

import argparse
import json
import os
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


def _command(args: argparse.Namespace, task_name: str, gpu_id: str, output_dir: Path) -> list[str]:
    command = [
        "uv",
        "run",
        "--no-sync",
        "python",
        str(SEARCH_ENTRY),
        "--task-name",
        task_name,
        "--phases",
        "clean,random",
        "--gpu-ids",
        gpu_id,
        "--seed",
        str(args.seed),
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
    ]
    if args.dataset_stats_path:
        command.extend(["--dataset-stats-path", args.dataset_stats_path])
    return command


def _terminate(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-name", required=True, help="Name of the matching docs/experiments directory.")
    parser.add_argument("--task-names", required=True, help="Comma-separated RoboTwin task names.")
    parser.add_argument("--gpu-ids", required=True, help="Comma-separated physical GPU ids.")
    parser.add_argument("--max-tasks-per-gpu", type=int, default=2)
    parser.add_argument("--task-timeout-seconds", type=int, default=10 * 60 * 60)
    parser.add_argument("--poll-interval-seconds", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-seed-attempts", type=int, default=1000)
    parser.add_argument("--target-good-seeds", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--ckpt", default=DEFAULT_CHECKPOINT)
    parser.add_argument("--dataset-stats-path", default=None)
    parser.add_argument(
        "--database",
        default="evaluate_results/robotwin/seed_search/scheduler.sqlite3",
        help="Persistent SQLite queue database.",
    )
    parser.add_argument("--output-dir", required=True, help="New result root for this scheduler run.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    tasks = _parse_csv(args.task_names)
    gpu_ids = _parse_csv(args.gpu_ids)
    if len(tasks) != len(set(tasks)) or len(gpu_ids) != len(set(gpu_ids)):
        raise ValueError("--task-names and --gpu-ids must not contain duplicates.")
    if args.max_tasks_per_gpu <= 0 or args.task_timeout_seconds <= 0 or args.poll_interval_seconds <= 0:
        raise ValueError("Capacity, timeout, and poll interval must be positive.")

    database_path = _resolve_path(args.database)
    output_root = _resolve_path(args.output_dir)
    if output_root.exists():
        raise FileExistsError(f"Output directory already exists: {output_root}")
    output_root.mkdir(parents=True)
    launcher_logs = output_root / "launcher_logs"
    launcher_logs.mkdir()
    scheduler_log = output_root / "scheduler.log"
    run_config = vars(args) | {"task_names": tasks, "gpu_ids": gpu_ids, "created_at": _now()}
    (output_root / "scheduler-run-config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    connection = _connect(database_path)
    existing = connection.execute("SELECT 1 FROM experiments WHERE name = ?", (args.experiment_name,)).fetchone()
    if existing:
        raise ValueError(f"Experiment already exists in SQLite queue: {args.experiment_name}")
    connection.execute(
        "INSERT INTO experiments(name, created_at, config_json) VALUES (?, ?, ?)",
        (args.experiment_name, _now(), json.dumps(run_config, ensure_ascii=False)),
    )
    for task_name in tasks:
        connection.execute(
            "INSERT INTO jobs(experiment_name, task_name, status, output_dir) VALUES (?, ?, 'queued', ?)",
            (args.experiment_name, task_name, str(output_root / task_name)),
        )
    connection.commit()
    _event(connection, scheduler_log, None, "scheduler_started", f"experiment={args.experiment_name} tasks={','.join(tasks)}")
    if args.dry_run:
        _event(connection, scheduler_log, None, "dry_run", "jobs queued without launching subprocesses")
        return

    running: dict[int, tuple[subprocess.Popen[Any], float, str]] = {}
    slots = [gpu_id for _ in range(args.max_tasks_per_gpu) for gpu_id in gpu_ids]
    try:
        while True:
            for job_id, (process, started, task_name) in list(running.items()):
                return_code = process.poll()
                elapsed = time.monotonic() - started
                if return_code is None and elapsed < args.task_timeout_seconds:
                    continue
                row = connection.execute("SELECT gpu_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
                gpu_id = str(row["gpu_id"])
                if return_code is None:
                    _terminate(process)
                    connection.execute(
                        "UPDATE jobs SET status='timed_out', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                        (_now(), process.returncode, f"task exceeded {args.task_timeout_seconds} seconds", job_id),
                    )
                    _event(connection, scheduler_log, job_id, "timed_out", f"task={task_name} gpu={gpu_id}")
                elif return_code == 0:
                    connection.execute(
                        "UPDATE jobs SET status='completed', finished_at=?, exit_code=? WHERE id=?",
                        (_now(), return_code, job_id),
                    )
                    _event(connection, scheduler_log, job_id, "completed", f"task={task_name} gpu={gpu_id}")
                else:
                    connection.execute(
                        "UPDATE jobs SET status='failed', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                        (_now(), return_code, f"subprocess exited with {return_code}", job_id),
                    )
                    _event(connection, scheduler_log, job_id, "failed", f"task={task_name} gpu={gpu_id} exit_code={return_code}")
                del running[job_id]

            used = [gpu_id for _, _, gpu_id in running.values()]
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
                command = _command(args, str(row["task_name"]), gpu_id, task_output)
                log_handle = (launcher_logs / f"{row['task_name']}.log").open("w", encoding="utf-8")
                process = subprocess.Popen(
                    command,
                    cwd=PROJECT_ROOT,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                log_handle.close()
                connection.execute(
                    "UPDATE jobs SET status='running', gpu_id=?, started_at=?, command_json=? WHERE id=?",
                    (gpu_id, _now(), json.dumps(command), row["id"]),
                )
                _event(connection, scheduler_log, int(row["id"]), "started", f"task={row['task_name']} gpu={gpu_id} pid={process.pid}")
                running[int(row["id"])] = (process, time.monotonic(), str(row["task_name"]))
                used.append(gpu_id)

            queued = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE experiment_name=? AND status='queued'", (args.experiment_name,)
            ).fetchone()[0]
            if not running and queued == 0:
                break
            time.sleep(args.poll_interval_seconds)
    except KeyboardInterrupt:
        for job_id, (process, _, task_name) in running.items():
            _terminate(process)
            connection.execute(
                "UPDATE jobs SET status='cancelled', finished_at=?, exit_code=?, error_text=? WHERE id=?",
                (_now(), process.returncode, "scheduler interrupted", job_id),
            )
            _event(connection, scheduler_log, job_id, "cancelled", f"task={task_name}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
