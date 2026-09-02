"""Evaluate one RoboTwin task across fixed friction values and archived seeds."""

from __future__ import annotations

import argparse
import csv
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from . import search_robotwin_seeds as search
    from . import validate_robotwin_successful_seeds as validate
except ImportError:
    import search_robotwin_seeds as search
    import validate_robotwin_successful_seeds as validate


DEFAULT_MANIFEST_DIR = (
    search.PROJECT_ROOT
    / "docs"
    / "experiments"
    / "2026-08-27-robotwin-all-tasks-seed-search"
    / "successful-seeds"
)
DEFAULT_FRICTION_VALUES = "0.05,0.20,0.35,0.50,0.65,0.80,0.95"


def _parse_friction_values(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("--friction-values must contain at least one value.")
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Friction values must be finite and non-negative.")
    if len(values) != len(set(values)):
        raise ValueError("Friction values must not contain duplicates.")
    return values


def _result_path(output_dir: Path, phase: str, friction: float, environment_seed: int) -> Path:
    friction_tag = format(friction, ".12g").replace(".", "p")
    return output_dir / "results" / phase / f"friction_{friction_tag}" / f"seed_{environment_seed}.json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--gpu-id", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--phases", default="clean,random")
    parser.add_argument("--friction-values", default=DEFAULT_FRICTION_VALUES)
    parser.add_argument("--seeds-per-phase", type=int, default=3)
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
    parser.add_argument(
        "--skip-get-obs-within-replan", action=argparse.BooleanOptionalAction, default=True
    )
    return parser


def _make_config(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = search._resolve_path(args.manifest)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = validate._load_manifest(manifest_path)
    phases = search._parse_csv(args.phases)
    if set(phases) - set(manifest["phases"]):
        raise ValueError(f"Requested phases are not present in manifest: {phases}")
    if args.seeds_per_phase <= 0:
        raise ValueError("--seeds-per-phase must be positive.")
    for phase in phases:
        available = len(manifest["phases"][phase]["successful_seeds"])
        if available < args.seeds_per_phase:
            raise ValueError(
                f"Manifest phase {phase!r} contains {available} seeds, "
                f"fewer than requested {args.seeds_per_phase}."
            )

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
            / "friction_sweep"
            / f"{manifest['task_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    return {
        "task_name": manifest["task_name"],
        "phases": phases,
        "friction_values": _parse_friction_values(args.friction_values),
        "seeds_per_phase": args.seeds_per_phase,
        "base_seed": manifest["policy_seed"],
        "repeats": 1,
        "ckpt": str(checkpoint),
        "dataset_stats_path": str(
            search._resolve_dataset_stats(checkpoint, args.dataset_stats_path)
        ),
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
        "gpu_id": str(args.gpu_id),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "git_revision": search._git_revision(),
    }


def _row(result: dict[str, Any]) -> dict[str, Any]:
    rollouts = result["rollouts"]
    success = bool(result["expert"]["ok"] and rollouts and rollouts[0]["success"])
    return {
        "task_name": result["task_name"],
        "phase": result["phase"],
        "friction": result["friction"],
        "static_friction": result["static_friction"],
        "dynamic_friction": result["dynamic_friction"],
        "environment_seed": result["environment_seed"],
        "policy_seed": result["policy_seed"],
        "expert_ok": result["expert"]["ok"],
        "rollout_success": bool(rollouts and rollouts[0]["success"]),
        "success": success,
        "steps": rollouts[0]["steps"] if rollouts else None,
        "gpu_id": result["gpu_id"],
        "error": result["error"] or (rollouts[0]["error"] if rollouts else None),
    }


def _write_outputs(output_dir: Path, config: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else [
        "task_name",
        "phase",
        "friction",
        "static_friction",
        "dynamic_friction",
        "environment_seed",
        "policy_seed",
        "expert_ok",
        "rollout_success",
        "success",
        "steps",
        "gpu_id",
        "error",
    ]
    with (output_dir / "results.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    phases: dict[str, dict[str, Any]] = {}
    for phase in config["phases"]:
        phase_rows = [row for row in rows if row["phase"] == phase]
        by_friction: dict[str, dict[str, Any]] = {}
        for friction in config["friction_values"]:
            cell = [row for row in phase_rows if row["friction"] == friction]
            successes = sum(bool(row["success"]) for row in cell)
            by_friction[format(friction, ".12g")] = {
                "seed_count": len(cell),
                "successes": successes,
                "success_rate": successes / len(cell) if cell else None,
            }
        phase_successes = sum(bool(row["success"]) for row in phase_rows)
        phases[phase] = {
            "trial_count": len(phase_rows),
            "successes": phase_successes,
            "mean_success_rate": phase_successes / len(phase_rows) if phase_rows else None,
            "by_friction": by_friction,
        }
    total_successes = sum(bool(row["success"]) for row in rows)
    search._atomic_json(
        output_dir / "summary.json",
        {
            "updated_at": search._now(),
            "task_name": config["task_name"],
            "trial_count": len(rows),
            "successes": total_successes,
            "mean_success_rate": total_successes / len(rows) if rows else None,
            "phases": phases,
        },
    )


def main() -> None:
    args = _build_parser().parse_args()
    config = _make_config(args)
    output_dir = Path(config["output_dir"])
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory already contains data: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    search._ensure_policy_symlink(Path(config["robotwin_root"]))
    search._atomic_json(output_dir / "run_config.json", {"created_at": search._now(), **config})

    os.environ["CUDA_VISIBLE_DEVICES"] = config["gpu_id"]
    os.environ["PYTHONUNBUFFERED"] = "1"
    runtime = search._prepare_runtime(config)
    rows: list[dict[str, Any]] = []
    for phase in config["phases"]:
        seeds = config["manifest"]["phases"][phase]["successful_seeds"][
            : config["seeds_per_phase"]
        ]
        for friction in config["friction_values"]:
            trial_config = {
                **config,
                "static_friction": friction,
                "dynamic_friction": friction,
            }
            for seed_record in seeds:
                environment_seed = int(seed_record["environment_seed"])
                result = search._evaluate_candidate(
                    runtime, trial_config, phase, environment_seed, config["gpu_id"]
                )
                result["friction"] = friction
                result["static_friction"] = friction
                result["dynamic_friction"] = friction
                search._atomic_json(
                    _result_path(output_dir, phase, friction, environment_seed), result
                )
                row = _row(result)
                rows.append(row)
                print(
                    f"task={config['task_name']} phase={phase} friction={friction:.2f} "
                    f"seed={environment_seed} success={row['success']}",
                    flush=True,
                )

    _write_outputs(output_dir, config, rows)
    print(f"finished summary={output_dir / 'summary.json'}", flush=True)


if __name__ == "__main__":
    main()
