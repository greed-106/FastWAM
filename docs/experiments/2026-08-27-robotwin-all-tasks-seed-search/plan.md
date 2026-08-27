# RoboTwin 全任务高成功率 Seed 搜索任务书

## 目标

本阶段在 RoboTwin 中对 `third_party/RoboTwin/task_config/_eval_step_limit.yml` 所列、且尚未在前一阶段完成 seed 搜索的任务进行环境 seed 筛选。清单共有 50 个任务；排除已经完成的 `click_bell` 后，本阶段目标为其余 49 个任务。

对每个任务的 clean 与 random 阶段分别寻找 10 个高质量环境 seed。每阶段最多枚举 1000 个连续候选环境 seed；候选只有在专家规划可行，且 5 次策略 rollout 均成功时才会入选。目标是筛选可复现的高成功率初始环境，不是估计任务总体成功率。

## 固定实验协议

| 项目 | 设定 |
| --- | --- |
| 策略与权重 | `fastwam_policy`，`checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt` |
| 阶段 | clean：`demo_clean` + `seen`；random：`demo_randomized` + `unseen` |
| 每阶段目标 | 10 个高质量环境 seed |
| 每候选 rollout | 5 次；仅 5/5 成功才入选 |
| 外部与策略采样 seed | `42` |
| 候选环境 seed | `4300000…4300999`，共 1000 个 |
| GPU 计划 | GPU `0,1,2,3,4,5,6,7`，每卡最多两个搜索进程 |

RoboTwin 将外部 seed $s$ 映射为起始环境 seed：

$$
\mathrm{environment\_seed}=100000\times(1+s).
$$

因此 $s=42$ 时从 `4300000` 开始。五次 rollout 均沿用固定的策略采样 seed `42`；它们检验同一环境 seed 下的独立重置与执行稳定性，不代表已覆盖五种不同的策略采样噪声。

## 实施与并发

`experiments/robotwin/search_robotwin_seeds.py` 支持任意单个任务的有界 clean/random 搜索、逐候选 JSON/CSV 结果和轻量 YAML 清单。跨任务 seed 搜索唯一使用 `experiments/robotwin/schedule_robotwin_seed_search.py`：它以 SQLite 保存本稳定实验目录名下的任务队列与事件历史，动态向指定 GPU 的空闲容量派发单 GPU 搜索子进程。每个任务的墙钟上限为 10 小时；正常完成、子进程失败、超时关闭均写入调度器日志和 SQLite。调度器不自动恢复或重试。

初始的 tmux 固定槽位批处理已暴露出槽位无法跨队列接管、单个 worker 停滞会长期占用槽位的问题，其启动脚本已删除。该批处理的结果、任务配置和日志保留为本阶段历史证据；后续任务不再使用 tmux 静态分配。

## 成功清单与完成标准

每个任务目录生成独立的 `successful-seeds.yaml`。它仅包含跨服务器固定 seed 复测所需的 `task_name`、相对 `checkpoint`、`policy_seed`，以及每个阶段的 `task_config`、`instruction_type` 和 `successful_seeds`。每个 seed 是含 `environment_seed` 与 `consecutive_successes` 的对象；验证器按该 seed 自身的连续成功次数执行复测。搜索命令的 `--repeats` 仍定义本次搜索协议，但不写入 YAML；逐候选证据保留在运行目录中。

批处理完成后，恢复会话时核验每个任务的 YAML 和 `summary.json`：报告 clean/random 实际入选数量、未达到 10 个 seed 的任务、专家规划失败、策略 rollout 失败和运行异常。整个阶段完成后再写 `summary.md`。

## 启动与验证

先以一个新任务、一个候选 seed、一次 rollout 做一次最小 smoke test，确认该任务的资产、模型和通用入口可运行；后续批量搜索使用全局调度器。例如：

```bash
uv run --no-sync python experiments/robotwin/schedule_robotwin_seed_search.py \
  --experiment-name <experiment-directory-name> \
  --task-names task_a,task_b \
  --gpu-ids 0,1,2,3,4,5,6,7 \
  --max-tasks-per-gpu 2 \
  --task-timeout-seconds 36000 \
  --seed 42 \
  --max-seed-attempts 1000 \
  --target-good-seeds 10 \
  --repeats 5 \
  --output-dir evaluate_results/robotwin/seed_search/<run-name>
```

启动后无需由 Codex 持续跟踪；用户可在任务结束后手动恢复会话。若需低频观察运行状态，使用 `sleep 300` 间隔，而非高频轮询。
