# RoboTwin 全任务高成功率 Seed 搜索主账本

## 实验标识

- 稳定项目目录：`docs/experiments/2026-08-27-robotwin-all-tasks-seed-search/`
- 启动日期：2026-08-27
- 当前状态：初始静态批处理已按用户指示停止且其启动脚本已删除；SQLite 全局队列中的 2 个任务已完成，6 个任务仍在运行。
- 任务书：[plan.md](plan.md)

## 目标

排除已有完成结果的 `click_bell`，为 RoboTwin 其余 49 个评测任务分别在 clean 与 random 阶段寻找 10 个高质量环境 seed。每阶段最多检查 1000 个连续候选环境 seed；每个入选 seed 都必须先通过专家规划，并在固定策略采样 seed `42` 下完成 5/5 次策略 rollout。使用发布权重 `checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt`。

## 当前代码支持

- `experiments/robotwin/search_robotwin_seeds.py` 支持单个 RoboTwin 任务的有界、可参数化 clean/random seed 搜索，并写入逐候选 JSON、汇总 JSON/CSV 与轻量 `successful-seeds.yaml`。
- `experiments/robotwin/validate_robotwin_successful_seeds.py` 可读取上述 YAML，对其中的固定环境 seed 进行复测。
- `experiments/robotwin/schedule_robotwin_seed_search.py` 是当前唯一的跨任务 seed 搜索入口；它将 GPU 容量限制、任务超时和 SQLite 队列状态参数化。
- 旧的 tmux 静态批处理启动器已删除；其历史结果和日志保留，不影响当前 SQLite 队列。

以上是当前代码能力描述，不表示本阶段的 GPU 任务已经执行。

## 本阶段实际执行

| 时间（Asia/Shanghai） | 事项 | 结果与证据 |
| --- | --- | --- |
| 2026-08-27 | 启动前检查 | 已阅读项目规范和前一阶段 `click_bell` 账本；工作树干净，当前分支为 `find-successful-seeds`。 |
| 2026-08-27 | 调度、结果与资源检查 | 未发现可用的 `squeue`、`sbatch`、`qstat` 或 `bjobs`；无 RoboTwin/FastWAM 搜索进程；`evaluate_results/robotwin/seed_search/` 仅有 `click_bell` 历史结果。GPU `0–7` 当时均空闲。 |
| 2026-08-27 | 任务范围确认 | `_eval_step_limit.yml` 含 50 个任务；排除已有完成结果的 `click_bell` 后，本阶段为 49 个任务。 |
| 2026-08-27 | 批处理入口与实验文档 | 新增 tmux 批处理启动器及本稳定实验目录。每个任务独占结果目录和 launcher 日志，每个槽位独占状态文件。 |
| 2026-08-27 02:12 +08:00 | 静态检查 | `bash -n`、启动器 `--help`、49 任务 dry-run 和原有搜索脚本的 `py_compile`/`--help` 均通过；dry-run 确认 GPU `0–7`、每卡两个槽位共 16 槽位。重复 GPU ID 被显式拒绝。 |
| 2026-08-27 02:12–02:15 +08:00 | 新任务 smoke test | 使用 GPU 0 对 `click_alarmclock` 运行 clean/random、每阶段 1 个候选环境 seed、每候选 1 次 rollout。两阶段的 `4300000` 均专家可行且 1/1 成功；结果位于 `evaluate_results/robotwin/seed_search/all_tasks_smoke_click_alarmclock_20260827_021245/`，并已生成轻量 YAML。 |
| 2026-08-27 02:16 +08:00 | 提交正式全任务搜索 | 通过 tmux 会话 `robotwin-seed-search-all-20260827` 启动 49 个任务。参数为 GPU `0–7`、每卡 2 槽位、base/policy seed `42`、每阶段 1000 个候选、目标 10、每候选 5 次 rollout。运行根目录：`evaluate_results/robotwin/seed_search/all_tasks_seed42_20260827_021627/`。 |
| 2026-08-27 02:16 +08:00 | 启动确认 | tmux 会话存在；16 个初始任务均已建立独立任务目录和 launcher 日志，且每张 GPU 上恰有两个搜索入口进程。此后按用户要求停止持续轮询。 |
| 2026-08-27 | 状态快照 | 49 个任务中，37 个以 exit code 0 完成，`open_laptop` 以 exit code 1 结束，5 个仍在运行，6 个尚未开始；即 38 个已进入终态、11 个尚未结束。 |
| 2026-08-27 | `open_laptop` 运行失败 | 该任务在连续搜索过程中其 GPU 6 worker 以 exit code `-11` 退出，主进程返回 1；launcher 日志在此前出现 pybind11 GIL 断言文本。已保留其 `run_config.json`、逐候选结果、summary 与 YAML，未自动重试或影响其他槽位。 |
| 2026-08-27 | 已结束结果审计 | 37 个正常结束任务的 clean 和 random 均已达到各 10 个严格 5/5 seed；没有任务因跑满 1000 个候选但数量不足 10 而正常结束。`open_laptop` 崩溃前每阶段仅处理 89 个候选，两个阶段均为 0 个 5/5、0 个 4/5 候选，因此不能把它归为“只差少量 seed”的情况。 |
| 2026-08-27 | 清理中断日志 | 按用户明确指示，删除旧 `open_laptop` 任务的 `manager.log`、GPU 6 worker 日志和任务 launcher 日志（共 3 个文件）；保留 `run_config.json`、逐候选结果、summary、YAML 及仍被后续任务使用的槽位共享日志/状态文件。 |
| 2026-08-27 10:29 +08:00 | 独立重跑 `open_laptop` | 使用空闲 GPU 0 以原协议重新启动：base/policy seed `42`、每阶段最多 1000 个候选、目标 10、每候选 5 次 rollout。tmux 会话 `robotwin-open-laptop-retry-20260827_102904` 和独立运行目录均已创建；不占用原批处理运行中的 GPU 4–7。 |
| 2026-08-27 | 后续状态快照 | 原 49 任务中，38 个 exit code 0 完成、2 个 exit code 1 失败、4 个仍运行、5 个尚未启动。38 个正常结束任务的两个阶段均已各达到 10 个严格 5/5 seed。 |
| 2026-08-27 | `put_object_cabinet` 运行失败 | 该任务的 GPU 6 worker 以 exit code `-11` 退出，前有 pybind11 GIL 断言文本；崩溃前 clean/random 各处理 274 个候选、各为 0 个 5/5 seed。其后同槽位已继续 `stack_bowls_two`，未自动重试。 |
| 2026-08-27 | 静态批处理终止与全局调度改造 | 用户要求将当时运行或尚未启动的 8 个任务重新运行。已结束旧 tmux 会话，保留旧结果和 105 个日志文件；停止的运行任务为 `move_stapler_pad`、`place_mouse_pad`、`stack_bowls_two`、`place_object_scale`，尚未启动任务为 `place_burger_fries`、`stack_blocks_two`、`stack_bowls_three`、`stamp_seal`。 |
| 2026-08-27 | 成功 seed 清单迁移 | 所有 45 份成功 seed YAML 已移除顶层 `repeats`；每个环境 seed 现在记录自身的 `consecutive_successes`。验证器只读取新结构；42 份含成功 seed 的清单已通过新读取器检查，3 份空清单保持为空。 |
| 2026-08-27 17:02 +08:00 | 首次全局调度器启动中断 | 外层启动进程未进入独立会话而提前退出，已立即结束其 8 个无监管子进程。首次启动的 SQLite 副本、调度日志、任务配置与 launcher 日志保留在 `global_scheduler_seed42_20260827_170235/`，未删除。 |
| 2026-08-27 17:04 +08:00 | SQLite 全局队列正式启动 | 使用独立会话启动调度器，任务超时为 10 小时、GPU `0–7`、每卡最多两个任务。8 个任务已分别开始于 GPU `0–7`；运行根目录为 `evaluate_results/robotwin/seed_search/global_scheduler_seed42_20260827_170411/`，持久队列为 `evaluate_results/robotwin/seed_search/scheduler.sqlite3`。 |
| 2026-08-27 17:57 +08:00 | 清理一次性迁移器与旧调度入口 | 确认验证器可读取 42 份非空新版 YAML，且当前运行进程仅调用 SQLite 调度器与搜索入口。删除一次性 `migrate_robotwin_successful_seed_manifests.py` 与 tmux 静态批处理启动器 `launch_robotwin_seed_search_batch.sh`；保留非 seed-search 的常规评测管理器 `run_robotwin_manager.py`。 |
| 2026-08-27 18:33–18:38 +08:00 | 全局队列完成两项任务 | `stack_blocks_two` 与 `place_burger_fries` 均以 exit code `0` 完成；两任务的 clean/random 均各入选 10 个连续 5/5 成功 seed，已写入各自运行目录的 `successful-seeds.yaml`、summary 和逐候选记录。 |

## 运行项

全局调度器以前台单进程方式执行，不使用 tmux；SQLite 队列按本实验稳定目录名区分历史任务，并向指定 GPU 的空闲容量动态派发。`move_stapler_pad`、`place_mouse_pad`、`stack_bowls_two`、`place_object_scale`、`stack_bowls_three` 与 `stamp_seal` 仍在运行；初始批处理的产物保留为历史证据。

## 失败项与资源问题

外部批处理调度器命令在当前环境不可用；这是环境事实，不是本实验失败。`open_laptop` 与 `put_object_cabinet` 的 native worker 均曾以 exit code `-11` 异常退出，并伴随 pybind11 GIL 断言文本；其配置和结果已保留，旧 `open_laptop` 任务级中断日志已按用户指示删除。

## 关键决策

- 默认外部/策略采样 seed 为 `42`，对应连续环境 seed `4300000…4300999`；策略 seed 不因 GPU、槽位或 rollout 次数偏移。
- clean 显式使用 `demo_clean` 与 `seen`，random 显式使用 `demo_randomized` 与 `unseen`。
- 全局调度器仍通过参数限制每卡并发数；每个任务独占结果目录和 launcher 日志，调度器将调度事件、完成、错误和超时写入 SQLite 与 `scheduler.log`。
- 一次性 YAML 迁移与 tmux 静态批处理入口均已删除；后续跨任务 seed 搜索只使用 SQLite 全局调度器。常规 RoboTwin 评测的 `run_robotwin_manager.py` 不属于 seed 搜索入口，继续保留。
- `click_bell` 已在前一稳定实验目录完成 seed 搜索与跨服务器复测，本阶段不重复提交。
- 用户要求正式批处理启动后由其手动恢复 Codex 查看结果，不做持续状态跟踪；如需观察，采用 `sleep 300` 低频等待。

## 产物位置

- 任务书：[plan.md](plan.md)
- 账本：本文件。
- 正式批处理结果：`evaluate_results/robotwin/seed_search/all_tasks_seed42_20260827_021627/`。
- `open_laptop` 重跑结果：`evaluate_results/robotwin/seed_search/open_laptop_retry_seed42_20260827_102904/`。

## 下一步

1. 等待 SQLite 队列中的其余 6 个重跑任务进入终态。
2. 核验每个任务的 YAML、汇总、失败记录和资源异常，再完成 `summary.md`。
