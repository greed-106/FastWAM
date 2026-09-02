"""Aggregate a completed 50-task RoboTwin friction sweep and write its report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd
import yaml

matplotlib.use("Agg")
from matplotlib import pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_DIR = (
    PROJECT_ROOT
    / "docs"
    / "experiments"
    / "2026-08-27-robotwin-all-tasks-seed-search"
    / "successful-seeds"
)
DEFAULT_DOC_DIR = (
    PROJECT_ROOT / "docs" / "experiments" / "2026-09-02-robotwin-friction-sweep"
)
FRICTION_VALUES = [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
PHASES = ["clean", "random"]


def _resolve_path(raw: str | Path) -> Path:
    path = Path(raw).expanduser()
    return (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _expected_seeds(manifest_dir: Path) -> dict[str, dict[str, list[int]]]:
    expected: dict[str, dict[str, list[int]]] = {}
    for path in sorted(manifest_dir.glob("*.yaml")):
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        task_name = manifest["task_name"]
        expected[task_name] = {
            phase: [
                int(item["environment_seed"])
                for item in manifest["phases"][phase]["successful_seeds"][:3]
            ]
            for phase in PHASES
        }
    if len(expected) != 50:
        raise ValueError(f"Expected 50 task manifests, found {len(expected)} in {manifest_dir}")
    return expected


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    mapped = series.astype(str).str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise ValueError("Boolean result column contains values other than true/false.")
    return mapped.astype(bool)


def _load_results(result_root: Path, expected: dict[str, dict[str, list[int]]]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for task_name, phase_seeds in expected.items():
        path = result_root / "jobs" / task_name / "results.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing task result: {path}")
        frame = pd.read_csv(path)
        if len(frame) != 42:
            raise ValueError(f"{task_name}: expected 42 rows, found {len(frame)}")
        frame["success"] = _as_bool(frame["success"])
        frame["expert_ok"] = _as_bool(frame["expert_ok"])
        frame["rollout_success"] = _as_bool(frame["rollout_success"])
        found_friction = sorted(float(value) for value in frame["friction"].unique())
        if found_friction != FRICTION_VALUES:
            raise ValueError(f"{task_name}: unexpected friction values {found_friction}")
        for phase in PHASES:
            phase_frame = frame[frame["phase"] == phase]
            if sorted(int(seed) for seed in phase_frame["environment_seed"].unique()) != sorted(
                phase_seeds[phase]
            ):
                raise ValueError(f"{task_name}/{phase}: evaluated seeds do not match manifest prefix")
            counts = phase_frame.groupby("friction").size().tolist()
            if counts != [3] * len(FRICTION_VALUES):
                raise ValueError(f"{task_name}/{phase}: expected three rows per friction value")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def _task_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for task_name, task_rows in results.groupby("task_name", sort=True):
        row: dict[str, Any] = {"task_name": task_name}
        for phase in PHASES:
            phase_rows = task_rows[task_rows["phase"] == phase]
            successes = int(phase_rows["success"].sum())
            row[f"{phase}_successes"] = successes
            row[f"{phase}_trials"] = len(phase_rows)
            row[f"{phase}_mean_success_rate"] = successes / len(phase_rows)
        successes = int(task_rows["success"].sum())
        row["successes"] = successes
        row["trials"] = len(task_rows)
        row["mean_success_rate"] = successes / len(task_rows)
        rows.append(row)
    return pd.DataFrame(rows)


def _friction_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for friction in FRICTION_VALUES:
        friction_rows = results[results["friction"] == friction]
        row: dict[str, Any] = {"friction": friction}
        for phase in PHASES:
            phase_rows = friction_rows[friction_rows["phase"] == phase]
            successes = int(phase_rows["success"].sum())
            row[f"{phase}_successes"] = successes
            row[f"{phase}_trials"] = len(phase_rows)
            row[f"{phase}_success_rate"] = successes / len(phase_rows)
        successes = int(friction_rows["success"].sum())
        row["successes"] = successes
        row["trials"] = len(friction_rows)
        row["success_rate"] = successes / len(friction_rows)
        rows.append(row)
    return pd.DataFrame(rows)


def _plot_task(task_name: str, task_rows: pd.DataFrame, phase: str, images_dir: Path) -> None:
    rates = (
        task_rows[task_rows["phase"] == phase]
        .groupby("friction", sort=True)["success"]
        .mean()
        .reindex(FRICTION_VALUES)
    )
    fig, axis = plt.subplots(figsize=(6.4, 4.0))
    axis.plot(FRICTION_VALUES, rates, marker="o", linewidth=2)
    axis.axvline(0.5, color="gray", linestyle="--", linewidth=1, label="default 0.50")
    axis.set(title=f"{task_name} — {phase}", xlabel="Friction", ylabel="Success rate")
    axis.set_xticks(FRICTION_VALUES)
    axis.set_ylim(-0.03, 1.03)
    axis.grid(alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(images_dir / f"{task_name}_{phase}.png", dpi=150)
    plt.close(fig)


def _plot_overall(friction_summary: pd.DataFrame, images_dir: Path) -> None:
    fig, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.plot(
        friction_summary["friction"],
        friction_summary["clean_success_rate"],
        marker="o",
        label="clean",
    )
    axis.plot(
        friction_summary["friction"],
        friction_summary["random_success_rate"],
        marker="o",
        label="random",
    )
    axis.plot(
        friction_summary["friction"],
        friction_summary["success_rate"],
        marker="o",
        linewidth=2.5,
        label="combined",
    )
    axis.axvline(0.5, color="gray", linestyle="--", linewidth=1, label="default 0.50")
    axis.set(title="RoboTwin 50-task friction sweep", xlabel="Friction", ylabel="Success rate")
    axis.set_xticks(FRICTION_VALUES)
    axis.set_ylim(0, 1)
    axis.grid(alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(images_dir / "overall_by_friction.png", dpi=160)
    plt.close(fig)


def _percentage(value: float) -> str:
    return f"{value:.2%}"


def _write_report(
    doc_dir: Path,
    result_root: Path,
    results: pd.DataFrame,
    task_summary: pd.DataFrame,
    friction_summary: pd.DataFrame,
) -> None:
    baseline = friction_summary[friction_summary["friction"] == 0.5].iloc[0]
    best_rate = float(friction_summary["success_rate"].max())
    best_values = friction_summary[friction_summary["success_rate"] == best_rate]["friction"].tolist()
    expert_failures = int((~results["expert_ok"]).sum())
    policy_failures = int((results["expert_ok"] & ~results["rollout_success"]).sum())
    lines = [
        "# RoboTwin 全任务摩擦参数扫描总结",
        "",
        "## 实验设置",
        "",
        "本实验同时改变 RoboTwin `scene.default_physical_material` 的静摩擦和动摩擦，扫描值为 "
        "`0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95`。`0.50` 是当前代码基线；ground、URDF "
        "和其他未显式使用该材质的碰撞体仍沿用 SAPIEN 默认材质，因此结论只针对 RoboTwin 声明材质。",
        "",
        "50 个任务的 clean/random 分别使用各自归档 YAML 中前三个环境 seed，每个 seed 运行一次，policy seed "
        "固定为 `42`。每个 task/phase/friction 单元的固定分母为 3；专家前检失败也计入失败。",
        "",
        "## 总体结果",
        "",
        f"合并 clean/random 后，最佳摩擦值为 {', '.join(f'`{value:.2f}`' for value in best_values)}，"
        f"总体成功率为 {_percentage(best_rate)}。默认值 `0.50` 的总体成功率为 "
        f"{_percentage(float(baseline['success_rate']))}，最佳点相对基线变化 "
        f"{(best_rate - float(baseline['success_rate'])) * 100:+.2f} 个百分点。",
        "",
        f"全部 2100 个固定试验槽位中，专家前检失败 {expert_failures} 次；专家通过但策略失败 "
        f"{policy_failures} 次。原始结果位于 `{result_root}`。",
        "",
        "![50 个任务总体摩擦曲线](images/overall_by_friction.png)",
        "",
        "| 摩擦值 | clean | random | 合并 |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for row in friction_summary.itertuples(index=False):
        lines.append(
            f"| {row.friction:.2f} | {row.clean_successes}/{row.clean_trials} "
            f"({_percentage(row.clean_success_rate)}) | {row.random_successes}/{row.random_trials} "
            f"({_percentage(row.random_success_rate)}) | {row.successes}/{row.trials} "
            f"({_percentage(row.success_rate)}) |"
        )

    lines.extend(
        [
            "",
            "## 逐任务平均成功率",
            "",
            "这里的 clean/random 平均值分别以 21 次试验为分母，总平均值以 42 次试验为分母。",
            "",
            "| 任务 | clean 平均 | random 平均 | 总平均 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in task_summary.itertuples(index=False):
        lines.append(
            f"| `{row.task_name}` | {row.clean_successes}/{row.clean_trials} "
            f"({_percentage(row.clean_mean_success_rate)}) | {row.random_successes}/{row.random_trials} "
            f"({_percentage(row.random_mean_success_rate)}) | {row.successes}/{row.trials} "
            f"({_percentage(row.mean_success_rate)}) |"
        )

    lines.extend(["", "## 逐任务曲线", ""])
    for row in task_summary.itertuples(index=False):
        lines.extend(
            [
                f"### `{row.task_name}`",
                "",
                f"clean 平均 {_percentage(row.clean_mean_success_rate)}，random 平均 "
                f"{_percentage(row.random_mean_success_rate)}，总平均 {_percentage(row.mean_success_rate)}。",
                "",
                f"![{row.task_name} clean 摩擦曲线](images/{row.task_name}_clean.png)",
                "",
                f"![{row.task_name} random 摩擦曲线](images/{row.task_name}_random.png)",
                "",
            ]
        )

    lines.extend(
        [
            "## 结论边界",
            "",
            "- 每个曲线点只有三个固定环境 seed，成功率分辨率为 $1/3$，适合观察趋势，不用于精细置信区间估计。",
            "- 使用的是此前筛选出的 successful seeds，因此结果衡量的是这些固定场景对摩擦变化的敏感性，不代表随机 seed 分布上的无偏成功率。",
            "- 摩擦只作用于 RoboTwin 声明材质，不能推广为所有场景接触面的统一摩擦扫描。",
            "",
        ]
    )
    (doc_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", required=True)
    parser.add_argument("--doc-dir", default=str(DEFAULT_DOC_DIR))
    parser.add_argument("--manifest-dir", default=str(DEFAULT_MANIFEST_DIR))
    args = parser.parse_args()

    result_root = _resolve_path(args.result_root)
    doc_dir = _resolve_path(args.doc_dir)
    manifest_dir = _resolve_path(args.manifest_dir)
    doc_dir.mkdir(parents=True, exist_ok=True)
    images_dir = doc_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    expected = _expected_seeds(manifest_dir)
    results = _load_results(result_root, expected)
    task_summary = _task_summary(results)
    friction_summary = _friction_summary(results)

    results.to_csv(doc_dir / "results.csv", index=False)
    task_summary.to_csv(doc_dir / "task-summary.csv", index=False)
    friction_summary.to_csv(doc_dir / "friction-summary.csv", index=False)
    (doc_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "task_count": len(task_summary),
                "trial_count": len(results),
                "task_summary": task_summary.to_dict(orient="records"),
                "friction_summary": friction_summary.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    for task_name, task_rows in results.groupby("task_name", sort=True):
        for phase in PHASES:
            _plot_task(task_name, task_rows, phase, images_dir)
    _plot_overall(friction_summary, images_dir)
    _write_report(doc_dir, result_root, results, task_summary, friction_summary)
    print(f"finished report={doc_dir / 'summary.md'}", flush=True)


if __name__ == "__main__":
    main()
