# RoboTwin 全任务高成功率 Seed 搜索主账本

## 实验标识

- 稳定项目目录：`docs/experiments/2026-08-27-robotwin-all-tasks-seed-search/`
- 启动日期：2026-08-27
- 当前状态：50 个 RoboTwin 任务的 successful seeds 搜索均已完成，稳定目录包含 50 份完整 YAML。后续扩展阶段重搜的 13 项也已全部完成并替换同名归档，13 份归档均与最终搜索产物 SHA256 一致。全部 50 个任务均已完成独立测试；40/50 个任务达到至少 90%，其中 22/50 达到 100%，统一成功率为 921/1000（92.10%）。当前没有运行项。
- 任务书：[plan.md](plan.md)

## 目标

排除已有完成结果的 `click_bell`，为 RoboTwin 其余 49 个评测任务分别在 clean 与 random 阶段寻找 10 个高质量环境 seed。每阶段最多检查 1000 个连续候选环境 seed；每个入选 seed 都必须先通过专家规划，并在固定策略采样 seed `42` 下完成 5/5 次策略 rollout。使用发布权重 `checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt`。

## 当前代码支持

- `experiments/robotwin/search_robotwin_seeds.py` 支持单个 RoboTwin 任务的有界、可参数化 clean/random seed 搜索，并写入逐候选 JSON、汇总 JSON/CSV 与轻量 `successful-seeds.yaml`；候选环境起点可单独覆盖，不改变策略采样 seed。
- seed-search 对同一候选的专家检查和全部策略 rollout 复用同一个 Python 任务实例，同时每次仍重新执行 `setup_demo()` 与 `close_env()`；这与官方 evaluator 的实例生命周期一致，并保留任务在 `play_once()` 中建立的派生状态。
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
| 2026-08-27 18:50 +08:00 | 全局队列完成 `stack_bowls_two` | 该任务以 exit code `0` 完成；clean 入选 10 个、random 入选 10 个连续 5/5 成功 seed（random 共发现 11 个满足 5/5 的候选，按目标仅选前 10 个）。 |
| 2026-08-27 19:13 +08:00 | 停止三项停滞搜索 | `move_stapler_pad`、`place_mouse_pad` 与 `stamp_seal` 分别在 GPU `0`、`1`、`7` 长时间无新候选落盘且 GPU 利用率为零。按用户指示只向这三个独立搜索进程组发送 `SIGTERM`；原调度器记录 exit code `143`，已落盘日志和结果保留。 |
| 2026-08-27 19:13 +08:00 | 跳过首个环境 seed 重跑 | 搜索器和全局调度器新增可选 `--environment-seed-start`，默认行为不变。以 policy seed `42`、环境起点 `4300001`、GPU `0,1,7`、每卡一个任务、10 小时超时启动三项重跑；独立队列为 `scheduler_env4300001_retry.sqlite3`，结果根目录为 `global_scheduler_seed42_env4300001_retry_20260827_1914/`。重跑调度器已脱离终端并开始记录任务日志。 |
| 2026-08-27 19:33 +08:00 | `place_mouse_pad` 重跑异常失败 | GPU `1` 的 worker 在处理完 clean 的 3 个候选和 random 的 3 个候选后，以 exit code `-6` 退出；搜索入口随之以 exit code `1` 结束，独立 SQLite 队列记录为 failed。逐候选结果、`manager.log` 和调度日志均保留。 |
| 2026-08-27 19:53 +08:00 | 全局队列完成 `stack_bowls_three` | 该任务以 exit code `0` 完成；clean 在 19 个候选中得到 10 个连续 5/5 seed，random 在 35 个候选中发现 11 个 5/5 seed、选取前 10 个，清单已写入任务目录。 |
| 2026-08-27 20:11 +08:00 | 运行状态核验 | `place_object_scale`（GPU `3`）仍正常推进，clean/random 均已处理 48 个候选但尚无 5/5 seed。重跑的 `move_stapler_pad` 与 `stamp_seal` 分别自 19:27 和 19:22 起无新候选结果，GPU `0`、`7` 利用率为零，进程仍存活，判定为停滞；未擅自终止或重启。 |
| 2026-08-27 22:02 +08:00 | `place_object_scale` 异常失败 | GPU `3` worker 在 clean/random 各处理 94 个候选、尚无 5/5 seed 后以 exit code `-11` 退出；搜索入口返回 exit code `1`，原 SQLite 队列记录为 failed。逐候选结果、`manager.log` 与调度日志均保留。 |
| 2026-08-27 22:34 +08:00 | 成功 seed 清单文档归档 | 按用户要求，将 44 个完整任务的 YAML 复制到 `successful-seeds/`，以 `<task>.yaml` 命名；原 `evaluate_results/` 中的清单保留。已逐份核验归档与原文件字节一致，且 clean/random 均含 10 个连续 5/5 seed。6 个未完成任务的部分或缺失清单未归档。 |
| 2026-08-28 23:38 +08:00 | 新驱动重试提交前审计 | 当前驱动为 `570.211.01`，8 张 H100 的显存占用与利用率均为 0，未发现 GPU 计算进程、全局调度器或 seed 搜索残留进程。当前工作区没有历史 `evaluate_results/robotwin/seed_search/`、SQLite 或任务结果；因此以账本和 `successful-seeds/` 归档确认 44 个任务已完成、目标 6 个任务尚无完整成功清单，并避免提交其他任务。工作树在修改账本前干净。 |
| 2026-08-28 23:40 +08:00 | 新驱动下重新提交 6 个未完成任务 | 使用现有全局 SQLite 调度器和 seed 搜索入口，按原始协议提交 `open_laptop`、`move_stapler_pad`、`place_object_scale`、`put_object_cabinet`、`place_mouse_pad`、`stamp_seal`。参数为 GPU `0–7`、每卡最多 1 个任务、任务超时 10 小时、base/policy seed `42`、默认环境起点 `4300000`、每阶段最多 1000 个候选、目标 10、每候选 5 次 rollout；发布权重保持不变。启动核验时 6 项均为 `running`，依次分配到 GPU `0–5`；GPU `6–7` 保持空闲。运行根目录为 `evaluate_results/robotwin/seed_search/driver570_retry_seed42_20260828_233951/`，独立队列为 `evaluate_results/robotwin/seed_search/scheduler_driver570_retry_20260828_233951.sqlite3`。提交后按用户要求不持续监控。 |
| 2026-08-29 00:23 +08:00 | 停止 3 个确定性无效搜索 | 逐候选 JSON 证明 `open_laptop`、`place_object_scale`、`put_object_cabinet` 的专家可行候选均在策略 rollout 首步分别因缺少 `arm_tag`、`arm_tag`、`origin_z` 而失败。根因不是调度参数缺失，而是 seed-search 为专家与 rollout 创建不同任务实例，丢失官方评测依赖的 `play_once()` 派生状态。按用户指示仅向这三项的独立进程组发送 `SIGTERM`；SQLite 于 00:23:26 将三项记为 `failed`、exit code `143`，该状态表示人工终止，不作为修复后搜索仍失败的结论。停止前 `open_laptop` clean/random 各处理 8 个候选，`place_object_scale` 各 9 个，`put_object_cabinet` 分别处理 38/37 个，均为 0 个 5/5 seed。结果与日志完整保留；`move_stapler_pad`、`place_mouse_pad`、`stamp_seal` 及调度器继续运行。 |
| 2026-08-29 00:25 +08:00 | 最小修复环境实例生命周期 | 只修改 `experiments/robotwin/search_robotwin_seeds.py`：每个候选仅构造一个任务实例，并把它依次传给专家检查和该候选的全部 rollout；没有增加 `arm_tag`、`origin_z` 任务特例，没有修改 vendored RoboTwin 任务代码，也没有改变 seed、重复次数、筛选标准或结果结构。固定 seed 验证器复用同一 `_evaluate_candidate()`，因此自动获得该修复，无需单独改动。 |
| 2026-08-29 00:25 +08:00 | 聚焦验证通过 | 使用纯内存 FakeEnv 验证专家阶段建立的派生状态可被后续两个 rollout 读取，且同一候选的环境工厂只调用一次；断言覆盖一次专家 `play_once()`、三次独立 `setup_demo()`/`close_env()` 和两个成功 rollout。`search_robotwin_seeds.py` 与 `validate_robotwin_successful_seeds.py` 的 `py_compile` 通过，`git diff --check` 通过。按用户要求未增加持久测试文件，也未运行 GPU smoke test。 |
| 2026-08-29 00:34 +08:00 | 生命周期修复后三任务重新提交 | 提交前核对确认三项旧任务均为人工终止的 `failed/143`，没有存活进程、成功 YAML 或其他排队/运行副本；行为审计确认修复只恢复官方 evaluator 使用的同实例派生属性，不改变环境 seed、场景重建、模型 reset、5 次重复、5/5 筛选标准、指令或结果结构。使用全新 SQLite 队列和输出目录，从默认环境 seed `4300000` 按原协议重新提交 `open_laptop`、`place_object_scale`、`put_object_cabinet`；任务超时 10 小时，GPU `0,2,3` 每卡一个。一次启动核验时三项均为 `running`，分别分配到 GPU `0,2,3`，且搜索进程启动时间晚于修复文件修改时间。队列为 `scheduler_lifecycle_fix_retry_20260829_003438.sqlite3`，结果根目录为 `lifecycle_fix_retry_seed42_20260829_003438/`；此后按用户要求不持续监控。 |
| 2026-08-29 01:01–01:11 +08:00 | 4 个任务正常完成 | `place_mouse_pad`、`open_laptop`、`stamp_seal`、`place_object_scale` 依次以 exit code `0` 完成。四项的 `summary.json`、`summary.csv` 与 `successful-seeds.yaml` 已做一致性核验：clean/random 均达到目标，各选择 10 个唯一环境 seed，每个均为严格 5/5，YAML 与 summary 中的 seed 顺序一致。并行收尾产生的额外 5/5 候选未超过目标入选数，符合现有筛选协议；四份清单尚未复制到稳定目录的 `successful-seeds/` 归档。 |
| 2026-08-29 01:15 +08:00 | 剩余两任务状态快照 | `move_stapler_pad`（GPU `1`）仍为 `running`，clean/random 各处理 13 个候选、分别入选 8/9；`put_object_cabinet`（GPU `3`）仍为 `running`，clean/random 各处理 42 个候选、分别入选 3/0。两项搜索进程与 GPU worker 均存活且候选仍在落盘；未发现新的 `AttributeError`、CUDA/OOM、worker 退出或调度异常。`put_object_cabinet` random 暂无入选的直接原因是当前 42 个候选均未通过专家阶段，不是生命周期属性缺失。 |
| 2026-08-29 01:25–01:27 +08:00 | `move_stapler_pad` 完成及最后一项状态 | `move_stapler_pad` 于 01:25:59 以 exit code `0` 完成；clean 处理 16 个候选、random 处理 14 个候选，两阶段均入选 10 个严格 5/5 seed。其 `summary.json`、`summary.csv` 与 `successful-seeds.yaml` 已完成一致性核验。当前仅 `put_object_cabinet`（GPU `3`）仍运行：01:27 快照时 clean 处理 54 个、入选 5 个，random 处理 53 个、入选 1 个；random 已产生严格 5/5 seed，进一步证明生命周期属性阻断已消除。任务进程和唯一 GPU compute PID 一致，日志持续更新，未发现新的崩溃或调度异常。 |
| 2026-08-29 01:33 +08:00 | 五份成功 seed 清单归档 | 按用户明确确认的“复制”语义，将 `open_laptop`、`move_stapler_pad`、`place_object_scale`、`place_mouse_pad`、`stamp_seal` 的 `successful-seeds.yaml` 复制到稳定目录 `successful-seeds/`，并以 `<task>.yaml` 命名；`evaluate_results/` 中的源清单保持不变。五份副本均与源文件 SHA256 一致。汇总从 44 份增加到 49 份唯一任务；逐份检查确认 clean/random 均各含 10 个唯一 seed，全部 `consecutive_successes: 5`，任务名、权重、policy seed 和阶段配置正确。仍在运行的 `put_object_cabinet` 未提前归档。 |
| 2026-08-29 04:22 +08:00 | `put_object_cabinet` 正常完成 | 任务于 04:22:02 以 exit code `0` 完成。clean 检查 148 个候选，其中 11 个通过专家、10 个达到 5/5并全部入选；random 检查 378 个候选，其中 12 个通过专家、10 个达到 5/5并全部入选。`summary.json`、`summary.csv`、逐候选 JSON 与 `successful-seeds.yaml` 的统计、seed 及顺序完全一致。 |
| 2026-08-29 10:47–10:48 +08:00 | 六任务最终审计与清单归档 | 两个有效队列中的 6 个任务均为 `completed`、exit code `0`；所有调度器、搜索、manager 和 worker 进程均已退出，GPU `0–7` 无 compute 进程、显存占用与利用率为零，最终日志未发现新的异常。六项共 12 个阶段均达到目标，各选取 10 个严格 5/5 seed。将 `put_object_cabinet/successful-seeds.yaml` 复制为稳定归档 `successful-seeds/put_object_cabinet.yaml`，源文件保持不变；归档由 49 份增加到 50 份唯一任务清单。 |
| 2026-08-29 15:00–15:01 +08:00 | 13 个低验证成功率任务重搜提交 | 现有 49 任务验证 summary 中严格低于 90% 的 13 项已按原协议重新搜索：policy seed `42`、环境起点 `4300000`、clean/random、每阶段最多 1000 候选、目标 10、每候选 5 次。作业与 `put_object_cabinet` 验证混合提交到同一个通用 SQLite 调度器，GPU `0–7`、每卡最多 2 项；启动快照中 13 项搜索均为 `running`。结果根目录为 `evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/`；新清单不会替换稳定归档。本行不表示搜索已经完成，此后不持续监控。 |
| 2026-08-29 18:31 +08:00 | 已完成重搜清单替换归档 | 恢复检查时 13 个重搜作业中已有 12 个完成，只有 `open_microwave` 仍在 GPU 6 运行。完成的 12 项均经 YAML、summary CSV 和入选候选记录核验：clean/random 各 10 个唯一 seed，每个都通过 expert 且策略 5/5。按用户新指示，用这 12 份清单替换稳定目录中的同名 YAML；11 份内容实际更新，`place_object_scale` 原归档已与新清单一致。替换后 12 份归档与源产物逐文件 SHA256 一致；仍在运行的 `open_microwave` 未替换。此前 15:00 行的“不替换”记录是提交时决策，本行记录后续明确变更。 |
| 2026-08-30 22:59 +08:00 | 第 13 项重搜归档与全范围测试终态 | `open_microwave` 搜索已于 01:00:02 正常完成，clean/random 各选出 10 个 expert 通过且策略严格 5/5 的 seed；最终 `successful-seeds.yaml` 已替换稳定归档，两者 SHA256 均为 `9af15327ef6ca4a3c9839f40af014544d8413982d4536691ea6c70a271e83b36`。复核全部 13 项重搜归档均与最终搜索产物逐文件一致，稳定目录仍为 50 份唯一任务 YAML。`open_microwave` 独立测试于 01:26:14 完成并取得 14/20；至此全部 50 个任务均已完成测试，40/50（80%）达到至少 90%，其中 22/50 达到 100%，统一结果为 921/1000（92.10%）。完整测试表见后续验证项目 `docs/experiments/2026-08-29-robotwin-all-tasks-seed-validation/summary.md`。 |

## 运行项

当前没有运行项。原全任务搜索、13 项后续重搜和全部独立测试均已完成；所有相关调度器、搜索器和验证器进程均已退出。

## 失败项与资源问题

外部批处理调度器命令在原环境不可用；这是环境事实，不是本实验失败。`open_laptop` 与 `put_object_cabinet` 的 native worker 均曾以 exit code `-11` 异常退出，并伴随 pybind11 GIL 断言文本；其配置和结果在原运行环境中曾保留，旧 `open_laptop` 任务级中断日志已按用户指示删除。`move_stapler_pad`、`place_mouse_pad` 与 `stamp_seal` 的原队列 exit code `143` 是有依据的人工终止，不作为其 seed 搜索失败结论。跳过首个环境 seed 的 `place_mouse_pad` 重跑中，worker 以 `-6` 退出、搜索入口返回 `1`；`place_object_scale` 的 worker 以 `-11` 退出、搜索入口返回 `1`。旧账本最后记录的另外两个重跑进程已停滞；当前服务器没有旧进程或旧结果现场。更换驱动后的本次 6 任务测试未复现 native 崩溃，但最初暴露出 seed-search 为专家与 rollout 使用不同任务实例的代码缺陷；2026-08-29 新增的三项 exit code `143` 是用户授权停止无效搜索的历史记录，相关 partial results 不得提升为成功产物。最小修复后的有效重跑均正常完成。

## 关键决策

- 默认外部/策略采样 seed 为 `42`，对应连续环境 seed `4300000…4300999`；策略 seed 不因 GPU、槽位或 rollout 次数偏移。
- clean 显式使用 `demo_clean` 与 `seen`，random 显式使用 `demo_randomized` 与 `unseen`。
- 全局调度器仍通过参数限制每卡并发数；每个任务独占结果目录和 launcher 日志，调度器将调度事件、完成、错误和超时写入 SQLite 与 `scheduler.log`。
- `--environment-seed-start` 只覆盖候选环境序列；`--seed` 继续同时作为外部/base seed 与策略采样 seed。2026-08-27 的三项重跑显式保持 `--seed 42`，并从 `4300001` 开始。
- 2026-08-28 的驱动更换后重试用于检验原失败条件是否消失，因此恢复原协议的默认环境起点 `4300000`，不沿用上一轮为了绕开首个候选而设置的 `4300001`；策略 seed 仍为 `42`。
- 本次只有 6 个任务，使用 GPU `0–7` 且将每卡容量设为 1；FIFO 初始分配落在 GPU `0–5`，避免单卡并发并保留 GPU `6–7` 空闲。
- 环境生命周期修复采用候选级单实例复用，与官方 evaluator 一致；不复制环境对象的任意属性，也不在 vendored 任务中添加三个任务专用补丁。每次 rollout 仍独立执行 `setup_demo()`、模型 reset 和 `close_env()`。
- 一次性 YAML 迁移与 tmux 静态批处理入口均已删除；后续跨任务 seed 搜索只使用 SQLite 全局调度器。常规 RoboTwin 评测的 `run_robotwin_manager.py` 不属于 seed 搜索入口，继续保留。
- `click_bell` 已在前一稳定实验目录完成 seed 搜索与跨服务器复测，本阶段不重复提交。
- 用户要求正式批处理启动后由其手动恢复 Codex 查看结果，不做持续状态跟踪；如需观察，采用 `sleep 300` 低频等待。
- 后续 13 项重搜沿用原协议；13 份清单均在完成搜索和产物审计后替换稳定归档，并已分别完成独立测试。验证成功率只采用独立测试结果，不以搜索阶段的 5/5 直接替代。

## 产物位置

- 任务书：[plan.md](plan.md)
- 账本：本文件。
- 完整成功 seed 清单归档：`successful-seeds/`（50 份唯一任务的 `<task>.yaml` 副本；原始结果清单保留）。
- 正式批处理结果：`evaluate_results/robotwin/seed_search/all_tasks_seed42_20260827_021627/`。
- `open_laptop` 重跑结果：`evaluate_results/robotwin/seed_search/open_laptop_retry_seed42_20260827_102904/`。
- 新驱动重试结果：`evaluate_results/robotwin/seed_search/driver570_retry_seed42_20260828_233951/`。
- 新驱动重试队列：`evaluate_results/robotwin/seed_search/scheduler_driver570_retry_20260828_233951.sqlite3`。
- 生命周期修复后三任务重试结果：`evaluate_results/robotwin/seed_search/lifecycle_fix_retry_seed42_20260829_003438/`。
- 生命周期修复后三任务重试队列：`evaluate_results/robotwin/seed_search/scheduler_lifecycle_fix_retry_20260829_003438.sqlite3`。
- 低验证成功率任务重搜结果：`evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/jobs/<task>/`。
- 混合扩展批次 SQLite：`evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/scheduler.sqlite3`。

## 下一步

1. 当前没有待完成的搜索、归档或独立测试任务，不自动重试验证失败 seed。
2. 后续若改变驱动、依赖、策略权重或随机性协议，应启动新的实验项目复测，不能直接沿用当前成功率。
