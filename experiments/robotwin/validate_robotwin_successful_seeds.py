"""Validate the fixed RoboTwin successful-seed manifest on one or more GPUs."""

from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import os
import queue
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

try:
    from . import search_robotwin_seeds as search
except ImportError:
    import search_robotwin_seeds as search


DEFAULT_MANIFEST = (
    search.PROJECT_ROOT
    / "docs"
    / "experiments"
    / "2026-08-26-robotwin-click-bell-seed-search"
    / "click-bell-successful-seeds.yaml"
)


def _parse_gpu_ids(raw: str) -> list[str]:
    gpu_ids = [item.strip() for item in raw.split(",") if item.strip()]
    if not gpu_ids:
        raise ValueError("--gpu-ids must contain at least one GPU id.")
    if len(gpu_ids) != len(set(gpu_ids)):
        raise ValueError("--gpu-ids must not contain duplicates.")
    return gpu_ids


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        manifest = yaml.safe_load(file)
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a YAML mapping.")

    required = {"task_name", "checkpoint", "policy_seed", "repeats", "phases"}
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"Manifest is missing required fields: {sorted(missing)}")
    if not isinstance(manifest["task_name"], str) or not manifest["task_name"]:
        raise ValueError("Manifest task_name must be a non-empty string.")
    if not isinstance(manifest["checkpoint"], str) or not manifest["checkpoint"]:
        raise ValueError("Manifest checkpoint must be a non-empty string.")
    if isinstance(manifest["policy_seed"], bool) or not isinstance(manifest["policy_seed"], int):
        raise ValueError("Manifest policy_seed must be an integer.")
    if (
        isinstance(manifest["repeats"], bool)
        or not isinstance(manifest["repeats"], int)
        or manifest["repeats"] <= 0
    ):
        raise ValueError("Manifest repeats must be a positive integer.")

    phases = manifest["phases"]
    if not isinstance(phases, dict) or not phases:
        raise ValueError("Manifest phases must be a non-empty mapping.")
    unknown = set(phases) - set(search.PHASE_TO_TASK_CONFIG)
    if unknown:
        raise ValueError(f"Unsupported manifest phases: {sorted(unknown)}")
    for phase, phase_config in phases.items():
        if not isinstance(phase_config, dict):
            raise ValueError(f"Manifest phase {phase!r} must be a mapping.")
        if phase_config.get("task_config") != search.PHASE_TO_TASK_CONFIG[phase]:
            raise ValueError(f"Manifest phase {phase!r} has an unexpected task_config.")
        if phase_config.get("instruction_type") != search.PHASE_TO_INSTRUCTION[phase]:
            raise ValueError(f"Manifest phase {phase!r} has an unexpected instruction_type.")
        seeds = phase_config.get("successful_seeds")
        if not isinstance(seeds, list) or not seeds:
            raise ValueError(f"Manifest phase {phase!r} must contain successful_seeds.")
        if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
            raise ValueError(f"Manifest phase {phase!r} seeds must be integers.")
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"Manifest phase {phase!r} contains duplicate seeds.")
    return manifest


def _result_path(output_dir: Path, phase: str, environment_seed: int) -> Path:
    return output_dir / "results" / phase / f"seed_{environment_seed}.json"


def _write_summary(output_dir: Path, config: dict[str, Any], records: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    phases_summary: dict[str, dict[str, Any]] = {}
    for phase in config["phases"]:
        phase_records = sorted(
            (record for record in records if record["phase"] == phase),
            key=lambda record: int(record["environment_seed"]),
        )
        phases_summary[phase] = {
            "seed_count": len(phase_records),
            "total_rollouts": sum(record["rollout_count"] for record in phase_records),
            "successful_rollouts": sum(record["rollout_successes"] for record in phase_records),
            "all_seeds_passed": all(record["all_rollouts_success"] for record in phase_records),
        }
        for record in phase_records:
            rows.append(
                {
                    "phase": phase,
                    "environment_seed": record["environment_seed"],
                    "policy_seed": record["policy_seed"],
                    "expert_ok": record["expert"]["ok"],
                    "rollout_successes": record["rollout_successes"],
                    "rollout_count": record["rollout_count"],
                    "success_rate": record["success_rate"],
                    "all_rollouts_success": record["all_rollouts_success"],
                    "gpu_id": record["gpu_id"],
                    "error": record["error"],
                }
            )

    search._atomic_json(
        output_dir / "summary.json",
        {
            "updated_at": search._now(),
            "task_name": config["task_name"],
            "policy_seed": config["base_seed"],
            "repeats": config["repeats"],
            "phases": phases_summary,
        },
    )
    with (output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def _evaluate(runtime: dict[str, Any], config: dict[str, Any], phase: str, environment_seed: int, gpu_id: str) -> dict[str, Any]:
    result = search._evaluate_candidate(runtime, config, phase, environment_seed, gpu_id)
    result["rollout_count"] = len(result["rollouts"])
    result["rollout_successes"] = sum(bool(rollout["success"]) for rollout in result["rollouts"])
    result["success_rate"] = result["rollout_successes"] / config["repeats"]
    return result


def _worker(config: dict[str, Any], gpu_id: str, tasks: Any, messages: Any, log_path: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id
    os.environ["PYTHONUNBUFFERED"] = "1"
    worker_log = Path(log_path)
    worker_log.parent.mkdir(parents=True, exist_ok=True)
    with worker_log.open("w", encoding="utf-8") as log_file, redirect_stdout(log_file), redirect_stderr(log_file):
        try:
            runtime = search._prepare_runtime(config)
            print(f"[{search._now()}] model ready on physical GPU {gpu_id}", flush=True)
            messages.put({"kind": "ready", "gpu_id": gpu_id})
        except Exception:
            messages.put({"kind": "worker_error", "gpu_id": gpu_id, "error": traceback.format_exc()})
            return

        while (task := tasks.get()) is not None:
            phase, environment_seed = task
            try:
                messages.put({"kind": "result", "result": _evaluate(runtime, config, phase, environment_seed, gpu_id)})
            except Exception:
                messages.put({"kind": "worker_error", "gpu_id": gpu_id, "error": traceback.format_exc()})
                return
        messages.put({"kind": "done", "gpu_id": gpu_id})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--gpu-ids", default="0,1,2,3,4,5,6,7")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--dataset-stats-path", default=None)
    parser.add_argument("--sim-task", default="robotwin_uncond_3cam_384_1e-4")
    parser.add_argument("--mixed-precision", choices=["no", "fp16", "bf16"], default="bf16")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--action-horizon", type=int, default=None)
    parser.add_argument("--replan-steps", type=int, default=24)
    parser.add_argument("--num-inference-steps", type=int, default=None)
    parser.add_argument("--sigma-shift", type=float, default=None)
    parser.add_argument("--text-cfg-scale", type=float, default=1.0)
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--rand-device", default="cpu")
    parser.add_argument("--skip-get-obs-within-replan", action=argparse.BooleanOptionalAction, default=True)
    return parser


def _make_config(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = search._resolve_path(args.manifest)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = _load_manifest(manifest_path)
    checkpoint = search._resolve_path(manifest["checkpoint"])
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    robotwin_root = search.PROJECT_ROOT / "third_party" / "RoboTwin"
    if not robotwin_root.is_dir():
        raise FileNotFoundError(f"RoboTwin root not found: {robotwin_root}")
    if args.output_dir:
        output_dir = search._resolve_path(args.output_dir)
    else:
        output_dir = (
            search.PROJECT_ROOT
            / "evaluate_results"
            / "robotwin"
            / "seed_validation"
            / f"{manifest['task_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    return {
        "task_name": manifest["task_name"],
        "phases": list(manifest["phases"]),
        "gpu_ids": _parse_gpu_ids(args.gpu_ids),
        "base_seed": manifest["policy_seed"],
        "repeats": manifest["repeats"],
        "ckpt": str(checkpoint),
        "dataset_stats_path": str(search._resolve_dataset_stats(checkpoint, args.dataset_stats_path)),
        "output_dir": str(output_dir),
        "robotwin_root": str(robotwin_root.resolve()),
        "sim_cfg_path": str((search.PROJECT_ROOT / "configs" / "sim_robotwin.yaml").resolve()),
        "sim_task": args.sim_task,
        "instruction_type": None,
        "mixed_precision": args.mixed_precision,
        "device": args.device,
        "action_horizon": args.action_horizon,
        "replan_steps": args.replan_steps,
        "num_inference_steps": args.num_inference_steps,
        "sigma_shift": args.sigma_shift,
        "text_cfg_scale": args.text_cfg_scale,
        "negative_prompt": args.negative_prompt,
        "rand_device": args.rand_device,
        "skip_get_obs_within_replan": args.skip_get_obs_within_replan,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "git_revision": search._git_revision(),
    }


def main() -> None:
    args = _build_parser().parse_args()
    config = _make_config(args)
    output_dir = Path(config["output_dir"])
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory already contains data: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    search._ensure_policy_symlink(Path(config["robotwin_root"]))
    search._atomic_json(output_dir / "run_config.json", {"created_at": search._now(), **config})

    tasks_to_run = [
        (phase, environment_seed)
        for phase, phase_config in config["manifest"]["phases"].items()
        for environment_seed in phase_config["successful_seeds"]
    ]
    print(
        f"validating task={config['task_name']} seeds={len(tasks_to_run)} repeats={config['repeats']} "
        f"gpus={','.join(config['gpu_ids'])}",
        flush=True,
    )

    context = mp.get_context("spawn")
    tasks = context.Queue()
    messages = context.Queue()
    for task in tasks_to_run:
        tasks.put(task)
    for _ in config["gpu_ids"]:
        tasks.put(None)

    workers: list[mp.Process] = []
    worker_gpu_ids: dict[int, str] = {}
    for gpu_id in config["gpu_ids"]:
        worker = context.Process(
            target=_worker,
            args=(config, gpu_id, tasks, messages, str(output_dir / "logs" / f"worker_gpu{gpu_id}.log")),
        )
        worker.start()
        workers.append(worker)
        assert worker.pid is not None
        worker_gpu_ids[worker.pid] = gpu_id

    records: list[dict[str, Any]] = []
    finished_gpu_ids: set[str] = set()
    worker_error: str | None = None
    try:
        while len(finished_gpu_ids) < len(workers):
            try:
                message = messages.get(timeout=10)
            except queue.Empty:
                exited = [
                    worker
                    for worker in workers
                    if worker.exitcode is not None and worker_gpu_ids[worker.pid] not in finished_gpu_ids
                ]
                if exited:
                    worker_error = "worker exited before reporting completion: " + ", ".join(
                        f"pid={worker.pid},exitcode={worker.exitcode}" for worker in exited
                    )
                    break
                continue
            if message["kind"] == "ready":
                print(f"worker ready gpu={message['gpu_id']}", flush=True)
            elif message["kind"] == "result":
                result = message["result"]
                records.append(result)
                search._atomic_json(_result_path(output_dir, result["phase"], result["environment_seed"]), result)
                print(
                    f"phase={result['phase']} seed={result['environment_seed']} "
                    f"success_rate={result['success_rate']:.1%} "
                    f"({result['rollout_successes']}/{config['repeats']})",
                    flush=True,
                )
            elif message["kind"] == "worker_error":
                worker_error = f"worker GPU {message['gpu_id']} failed:\n{message['error']}"
                break
            elif message["kind"] == "done":
                finished_gpu_ids.add(message["gpu_id"])
    finally:
        if worker_error:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
        for worker in workers:
            worker.join(timeout=30)
            if worker.is_alive():
                worker.kill()
                worker.join()

    _write_summary(output_dir, config, records)
    if worker_error:
        raise RuntimeError(worker_error)
    if len(records) != len(tasks_to_run):
        raise RuntimeError(f"Expected {len(tasks_to_run)} results, received {len(records)}.")
    print(f"finished summary={output_dir / 'summary.json'}", flush=True)


if __name__ == "__main__":
    main()
