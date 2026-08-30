# RoboTwin 全任务 Successful Seeds 验证主账本

## 实验标识

- 稳定项目目录：`docs/experiments/2026-08-29-robotwin-all-tasks-seed-validation/`
- 启动日期：2026-08-29
- 当前状态：50/50 个 RoboTwin 任务均已完成 successful seeds 搜索、稳定 YAML 归档和逐任务独立测试。`summary.md` 以单一大表维护每项最新结果：13 项重测结果替换旧行，`put_object_cabinet` 补验加入第 50 行，其余行保留最新已完成验证。统一结果为 921/1000（92.10%）；40/50 个任务达到至少 90%，其中 22/50 达到 20/20。全部调度器和验证任务均已完成。
- 任务书：[plan.md](plan.md)

## 目标

复测 49 份已归档 successful-seeds 清单，共 980 个环境 seed。每个 seed 按清单固定执行 5 次策略 rollout，总计 4900 次；统计
rollout、seed 与任务三个层级的复现成功情况。新增纳入的五个任务为 `move_stapler_pad`、`open_laptop`、`place_mouse_pad`、
`place_object_scale` 和 `stamp_seal`。

扩展阶段补验 `put_object_cabinet`，并在当前驱动环境下重新搜索原验证成功率严格低于 90% 的任务。此前完成重搜的 12 份新清单已按用户
后续指示替换稳定 successful-seeds 归档并完成独立验证；最后完成的 `open_microwave` 已产出合格搜索清单、替换稳定归档并完成独立验证。
项目最终范围为 50 个任务、1000 个归档环境 seed；每项均已有已完成测试结果。

## 当前代码支持

- `experiments/robotwin/validate_robotwin_successful_seeds.py` 可读取单份 YAML，在指定 GPU 上复测清单内的固定环境 seed，并写入逐 seed JSON、worker 日志及任务级 `summary.json`/`summary.csv`。
- `experiments/robotwin/schedule_robotwin_seed_search.py` 已增加通用 `--jobs-file` 接口。JSON 以 argv 数组描述任意 `uv run` 作业，可使用 `{gpu_id}`、`{job_name}`、`{output_dir}` 占位符；调度器本身不识别搜索或验证业务。顶层 `argv_template` 配合任务名列表可简洁描述同构批次，单项也可用自己的 `argv` 覆盖模板。
- 原有 `--task-names` seed-search 调用仍兼容；通用作业默认将 SQLite 放在本批次 `<output-dir>/scheduler.sqlite3`，旧搜索调用仍保留原默认数据库路径。不同调度器进程不会通过共享 SQLite 协调 GPU，因此本批次独占其声明的 GPU 池，禁止在相同 GPU 上并行启动第二个调度器。
- 调度器仅负责 FIFO、SQLite 状态、GPU 槽位、超时和每作业独立 launcher 日志；具体验证命令通过作业文件提交。RoboTwin 的 `fastwam_policy` 软链接将在正式并发派发前由单进程使用现有 helper 预创建和核验，而不是写成调度器的验证特例。
- seed-search 与固定 seed 验证共同使用候选级单任务实例生命周期修复；这使官方评测依赖的 `play_once()` 派生状态在专家检查后保留给 rollout。

以上描述当前代码能力；本阶段实际执行结果与代码能力分开记录如下。

## 本阶段实际执行

| 时间（Asia/Shanghai） | 事项 | 结果与证据 |
| --- | --- | --- |
| 2026-08-29 01:45 | 工作树检查 | 开始本阶段前，工作树已有用户应用 patch 带来的改动：seed-search 账本与搜索脚本已修改，五份新增 YAML 尚未跟踪。本阶段保留这些改动，不覆盖或整理无关文件。 |
| 2026-08-29 01:45 | 清单范围与协议核验 | `successful-seeds/` 中共有 49 份 YAML，文件名均与 `task_name` 一致；每份均含 clean/random，各阶段 10 个唯一环境 seed，每个均为 `consecutive_successes: 5`，且 `policy_seed` 均为 `42`。总计 980 个 seed、4900 次 rollout。新增五项均已包含。 |
| 2026-08-29 01:45 | 调度、结果与 GPU 检查 | 未发现 `schedule_robotwin_seed_search.py`、`validate_robotwin_successful_seeds.py` 或 `search_robotwin_seeds.py` 的存活任务进程；未发现既有 seed-validation 结果或 SQLite。GPU `0–7` 均为 H100 80GB，检查时显存占用为 0 MiB、利用率为 0%。正式提交前仍须重新检查，不能把本次快照视为持续资源保证。 |
| 2026-08-29 01:45 | 实验文档初始化 | 创建本稳定实验目录及中文 `plan.md`、`ledger.md`，记录一次性 SQLite 验证队列、每卡最多两个任务、单任务 10 小时超时和提交后不持续监控的约束。尚未修改代码、执行 dry-run 或提交任务。 |
| 2026-08-29 01:53 | 通用调度接口实现 | 按用户澄清，未保留验证专用模式。一次性 SQLite 调度器新增 `--jobs-file` 通用 argv 作业接口，并保留旧 seed-search CLI；同时修复旧实现把运行元组中的任务名误当作 GPU ID、导致 `--max-tasks-per-gpu` 容量统计失效的问题。通用接口默认将 SQLite 放在该批输出根目录，不再误用 seed-search 专用或跨进程共享的数据库路径。此项仅表示代码已修改，尚未完成 `py_compile`、`--help`、集成测试、dry-run 或正式提交。 |
| 2026-08-29 01:55 | 子进程清理加固 | 通用调度器的超时与异常清理改为轮询、回收主进程并终止其亲自启动的完整进程组，避免 `uv` 主进程先退出后 descendant 继续占用 GPU；子进程在 `Popen` 成功后立即纳入内存跟踪，父进程持有的 launcher 日志句柄由上下文管理器关闭。若调度循环自身异常，在跑作业会被终止并尽力记为 `cancelled`，不执行自动重试；超时错误也使用通用的 `job` 术语。尚待集成测试。 |
| 2026-08-29 01:58 | 终止状态一致性修复 | 调度器现在把 `SIGTERM` 转为受控中断；调度器异常或中断时会终止所有在跑进程组，并将本批次尚未派发的 queued 作业一并记为 `cancelled`，即使异常发生在首个子进程启动前也会记录原因。正常或异常退出的作业主进程进入终态前也会核验并清理同进程组残留 descendant，避免提前释放 GPU 槽位。尚待再次集成测试。 |
| 2026-08-29 01:58 | 验证作业配置 | 新增 `validation-jobs.json`，以一个通用 `argv_template` 和 49 个作业名描述本批验证。每项渲染为现有验证器命令，并显式使用对应 `{job_name}.yaml`、单张 `{gpu_id}` 和独立 `{output_dir}`；配置中没有验证专用调度参数。尚未执行 dry-run 或正式提交。 |
| 2026-08-29 01:59 | 通用接口冲突检查 | GPU ID 在分配前统一规范化为非负十进制索引，因此 `0` 与 `00` 会被识别为同一物理 GPU 并拒绝重复；通用作业结果统一置于 `<output-dir>/jobs/<job_name>/`，避免作业名与根目录的 `scheduler.log`、SQLite 或 launcher 元数据冲突。旧 seed-search 分支继续使用原任务输出布局，并在 run config 中保留解析后的 `task_names` 列表。尚待再次集成测试。 |
| 2026-08-29 02:00 | 资源关闭补强 | dry-run 与重复实验名错误路径显式关闭 SQLite；异常清理某个进程组失败时继续处理其余在跑作业，并把该项清理错误写入取消原因，避免单项清理异常中断整个清理循环。 |
| 2026-08-29 02:01 | SIGTERM 正常退出 | `SIGTERM` 完成 running/queued 取消与进程组清理后正常返回，避免预期的 systemd stop 留下 Python `KeyboardInterrupt` traceback；交互式 Ctrl-C 仍在清理后向调用者传播。 |
| 2026-08-29 02:01 | 任务书纠正 | `plan.md` 已移除先前未采用的验证专用 mode 描述，改为通用 `--jobs-file`、`validation-jobs.json`、`jobs/<task>/` 输出布局和提交前单进程 policy 软链接预检；没有把这些计划动作误写成已执行。 |
| 2026-08-29 02:02 | 通用调度器集成测试 | `py_compile`、调度器 `--help` 和 `git diff --check` 通过。无 GPU 临时作业证明：单 GPU 容量 2 时前两项时间区间重叠、第三项在槽位释放后才启动；成功、exit 7、1 秒超时分别落为 `completed`、`failed`、`timed_out`；`SIGTERM` 后一个 running 与两个 queued 均落为 `cancelled`，子进程 PID 已消失；`0,00` 重复物理 GPU 被拒绝。旧 seed-search 命令 argv 与参数顺序保持不变。临时证据位于 `/tmp/fastwam-scheduler-integration-20260829-0155/`，不是正式实验产物。 |
| 2026-08-29 02:02 | 49 项真实配置 dry-run | 通过通用 `--jobs-file` 创建临时 SQLite，恰有 49 个 queued、49 个唯一 `jobs/<task>/` 输出路径，未启动 launcher。逐项渲染确认对应 manifest、GPU 和输出目录正确，所有命令均实际使用 `{output_dir}`，渲染后无残留命名占位符；49 份 manifest 均经验证器 `_make_config` 通过，共 980 seeds、4900 rollouts。临时 dry-run 位于 `/tmp/fastwam-scheduler-integration-20260829-0155/validation-dry-run-v2/`；正式任务仍未提交。 |
| 2026-08-29 02:02 | policy 软链接预创建 | 调用现有 `_ensure_policy_symlink` 单进程创建并核验 `third_party/RoboTwin/policy/fastwam_policy -> /data/mjyang/code/FastWAM/experiments/robotwin/fastwam_policy`。创建前目标不存在，创建后为指向预期目录的软链接；正式并发尚未启动。 |
| 2026-08-29 02:03 | 正式提交前复查 | GPU `0–7` 均为 `0 MiB / 0%`，无搜索、验证或本调度器进程；正式 unit 与结果目录不存在，磁盘剩余约 13 TiB。外部 `vlm-token-queue.service` 仍为 active，但其目录计数为 pending 0、running 0、completed 62；该服务也声明 GPU `0–7`，若之后收到新任务会与本批产生跨调度器竞争，本阶段未获授权停止该服务。用户 linger 为 no，但检查时有 3 个会话。 |
| 2026-08-29 02:05 | 正式验证提交 | 通过 `robotwin-seed-validation-49-20260829.service` 提交一次性通用调度器；实验名为 `2026-08-29-robotwin-all-tasks-seed-validation`，作业来源为 `validation-jobs.json`，GPU `0–7`、每卡最多 2 项、单项超时 36000 秒。结果根目录为 `evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0203/`，SQLite 使用其中的 `scheduler.sqlite3`。本行仅记录 systemd 接受提交，队列与子任务状态待下一项一次性核验。 |
| 2026-08-29 02:05 | systemd 启动核验 | unit 一度为 active/running，MainPID `22698`、Python 调度器 PID `22701`；SQLite 恰有 running 16、queued 33，每张 GPU 正好分配 2 项，16 条渲染命令的 manifest/GPU/独立输出目录及 16 份 launcher 日志均正确。该快照只证明启动与调度容量正确，不表示 rollout 成功。 |
| 2026-08-29 02:06 | 按用户要求停止 systemd 方式 | 用户明确不希望使用 service。已执行受控停止；unit 随后为 `LoadState=not-found`、inactive/dead，未发现调度器或验证器残留进程，GPU 显存均为 0 MiB。该次 SQLite 中 49 项全部为 `cancelled`，生成的 `summary.json` 为 0；目录与日志保留作为取消证据，不复用、不删除。 |
| 2026-08-29 02:07 | 普通后台进程重提 | 重提前确认 GPU `0–7` 均空闲、无验证/调度进程，外部队列 pending/running 均为 0，新路径不存在。通过普通 `nohup + setsid` 重提通用调度器，launcher PID 为 `27190`；实验名为 `2026-08-29-robotwin-all-tasks-seed-validation-nosystemd`，结果根目录为 `evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0207/`。本行仅记录后台进程已创建，队列状态待一次性核验。 |
| 2026-08-29 02:08 | 普通后台进程启动核验 | launcher PID `27190` 存活，PPID 为 1、SID/PGID 均为 `27190`、无控制终端；其 Python 调度器 PID 为 `27193`，不存在 systemd unit。SQLite 恰有 running 16、queued 33，GPU `0–7` 各分配 2 项；49 个输出路径唯一，16 条已渲染命令的 manifest/GPU/输出参数正确，launcher 日志恰有 16 份且互不共享。该快照只证明启动和调度正确；尚未产生成功结论，此后不持续监控。 |
| 2026-08-29 10:52 | 正式批次完成与三层审计 | SQLite 中 49/49 作业均为 `completed`、exit code 0，事件为 started/completed 各 49；首项于 02:07:52 启动，末项于 05:00:52 结束，后台 PID 已退出且无调度/验证残留进程。49 个任务目录、49 份 run config、49 份 JSON/CSV 汇总、49 份 worker/launcher 日志及 980 份逐 seed JSON 全部齐全；逐 seed JSON、CSV、summary 三层重算一致，manifest/命令/GPU/输出映射无缺失、额外或重复。 |
| 2026-08-29 10:52 | 验证结果 | 886/980 个 seed 达到严格 5/5（90.41%），19/49 个任务达到 20/20；clean 为 445/490，random 为 441/490。计划 4900 个 rollout 槽位中成功 4430 个（90.41%）；60 个 seed 因 expert 前检失败使 300 次未执行，实际执行 4600 次、成功 4430 次（96.30%）。另有 34 个 expert 通过的 seed 为策略 0/5，共 170 次执行失败；没有 1–4/5 的中间态。 |
| 2026-08-29 11:06 | 阶段总结 | 新增 `summary.md`，记录两种 rollout 分母、clean/random 分项、19 个全通过任务、30 个未全过任务逐项统计、新增五任务结果、expert/策略失败分类、运行告警、产物位置与后续研究方向；没有自动重试失败 seed。 |
| 2026-08-29 13:45 | 逐任务成功率补充 | `summary.md` 新增覆盖全部 49 个任务的统一表格；逐项同时给出 clean/random 严格 5/5 seed 数、严格 seed 合计、以 100 个计划 rollout 槽位为分母的计划成功率、排除 expert 前检未执行项后的实跑成功率，以及 expert 失败和策略 0/5 seed 数。数据来自正式批次 49 份 `summary.csv`，未重跑任务。 |
| 2026-08-29 14:18 | 总结口径重写 | 按用户明确的定义重写 `summary.md`：逐任务测试成功率统一为成功 seed 数除以固定 20 个 seed；seed 只有重新通过 expert 前检且策略 5/5 才成功，expert 前检失败时后续 5 次 rollout 统一视为失败。删除计划/实跑两套成功率，补充每任务 20 个 seed 的构成、expert 前检含义、搜索阶段入选条件及 49 项统一结果表；未重跑任务。 |
| 2026-08-29 14:31 | seed-search final patch 重应用 | 为解决用户报告的 `git apply` 冲突，仅将上一版 patch 覆盖的 seed-search 账本、搜索脚本和 5 份未跟踪 YAML 恢复到 Git 基线/暂存移出，再干净应用 `fastwam-seed-search-final-18e0e6e.patch`。final patch 共覆盖 9 项，新增第 50 份清单 `put_object_cabinet.yaml` 和 seed-search `summary.md`；原 5 份 YAML 重应用前后 SHA256 一致，搜索脚本 `py_compile` 通过。第 50 份清单未包含在此前已完成的 49 任务验证批次中，本阶段没有自动提交新验证，既有 49 任务结果与总结保持不变。 |
| 2026-08-29 14:56 | 扩展范围与混合配置 | 从现有 `summary.md` 按“成功 seed 数/20”重算出 13 个严格低于 90% 的任务；恰好 90% 的任务未纳入。新增 `refresh-jobs.json`，以 1 个 `put_object_cabinet` 固定 seed 验证 argv 和 13 个原协议 seed-search argv 描述 14 项混合队列。搜索固定 seed `42`、环境起点 `4300000`、每阶段最多 1000 候选、目标 10、重复 5 次；选择 GPU `0–7`、每卡最多 2 项、单项超时 10 小时。新搜索结果不替换稳定清单。当前未执行 dry-run 或正式提交。 |
| 2026-08-29 14:59 | 静态检查与 14 项 dry-run | 调度器、搜索器、验证器的 `py_compile` 与 `--help` 通过；`put_object_cabinet` manifest 为 clean/random 各 10 个唯一严格 5/5 seed，13 个重搜任务与 summary 中 `<90%` 标记完全一致。通用调度 dry-run 在 `/tmp/fastwam-refresh-dry-run.9PKjwF/output/` 创建 14 个唯一 queued 作业和独立输出路径，未启动子进程；全部 argv 占位符可完整渲染，参数正确。按 16 个槽位模拟分配时 GPU `0–5` 各 2 项、`6–7` 各 1 项。正式任务尚未提交。 |
| 2026-08-29 15:00 | 扩展批次提交前复查 | 未发现 queued/running 的 RoboTwin SQLite 队列或相关进程；GPU `0–7` 均为 0 MiB、利用率 0%，磁盘剩余约 13 TiB。外部 `vlm-token-queue.service` 为 active，但其 pending/running 均为 0；本阶段未停止或修改该服务。正式结果根目录、launcher PID 和日志路径提交前均不存在。 |
| 2026-08-29 15:00–15:01 | 普通后台提交与启动核验 | 使用 `nohup + setsid` 提交通用调度器，不使用 systemd。launcher PID `525474`，PPID 为 1、SID/PGID 均为 `525474`；SQLite 快照为 14/14 `running`、started 事件 14 条，GPU `0–5` 各分配 2 项、`6–7` 各 1 项。14 个输出目录、14 份 launcher 日志、渲染后的 manifest/task/GPU/输出参数均正确且互不共享。结果根目录为 `evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/`。本行只证明任务已派发；此后不持续监控。 |
| 2026-08-29 18:27 | 扩展批次恢复检查 | 混合批次 SQLite 为 13 项 `completed`、1 项 `running`；唯一运行项是 GPU 6 上的 `open_microwave` 搜索。`put_object_cabinet` 验证为 18/20（90%）；其余 12 个搜索作业均已生成 `successful-seeds.yaml`，每份 clean/random 各 10 个唯一且严格 5/5 的 seed。GPU `0,1,2,3,4,5,7` 空闲，GPU 6 由上述搜索占用，外部 `vlm-token-queue.service` 为 inactive。 |
| 2026-08-29 18:31 | 重搜 seed 归档与验证配置 | 按用户要求，先将已完成重搜的 12 份新清单替换到稳定 `successful-seeds/` 归档；11 份内容发生变化，`place_object_scale` 已与新产物字节一致。替换后 12 份归档均与各自搜索产物 SHA256 一致。新增 `refreshed-seed-validation-jobs.json`，验证器读取这些归档并使用独立输出；计划只使用 GPU `0,1,2,3,4,5,7`、每卡最多 2 项，明确排除 GPU 6。此时尚未执行 dry-run 或正式提交。 |
| 2026-08-29 18:32 | 重搜 seed 验证静态检查与 dry-run | 调度器、验证器和搜索器的 `py_compile`、两个相关入口的 `--help` 及 `git diff --check` 通过。12 份稳定归档与搜索产物逐字节一致，均经验证器配置加载，共 24 个 phase、240 个 seed、1200 个固定 rollout 槽位。临时 SQLite dry-run 在 `/tmp/fastwam-refreshed-validation-dry-run.3hYz9I/output/` 产生恰好 12 个 queued 作业、12 个唯一输出且没有启动子进程；模拟首轮分配为 GPU `0,1,2,3,4` 各 2 项，GPU `5,7` 各 1 项，未使用 GPU 6。正式任务尚未提交。 |
| 2026-08-29 18:32-18:33 | 12 项重搜 seed 验证提交与启动核验 | 提交前 GPU `0,1,2,3,4,5,7` 空闲，GPU 6 仅运行 `open_microwave` 搜索，没有待验证任务的 queued/running 副本，外部 `vlm-token-queue.service` 为 inactive。使用普通 `nohup + setsid` 启动独立调度器，不使用 systemd；launcher PID `738136` 的 PPID 为 1，SID/PGID 均为 `738136`。SQLite 恰有 12 项 `running`：GPU `0,1,2,3,4` 各 2 项，GPU `5,7` 各 1 项，GPU 6 未使用；12 个输出和 12 份 launcher 日志均唯一，命令全部读取替换后的稳定归档。结果根目录为 `evaluate_results/robotwin/seed_validation/refreshed_successful_seeds_12_20260829_1833/`。本行只证明正常派发，不表示验证成功。 |
| 2026-08-29 23:29 | 12 项重搜 seed 验证完成与产物审计 | SQLite 为 12/12 `completed`、exit code 全为 0，started/completed 事件各 12 条；首项于 18:32:43 启动，末项于 20:02:28 结束，launcher PID `738136` 已退出且无验证器残留。12 个任务目录、12 份 run config、12 份 JSON/CSV summary、12 份 worker 日志、12 份 launcher 日志和 240 份逐 seed JSON 全部齐全。逐 seed JSON、CSV、summary、归档 YAML、GPU 和输出路径映射一致，无缺失、额外或重复。 |
| 2026-08-29 23:29 | 12 项重搜 seed 验证结果 | 固定分母口径下 clean 为 97/120、random 为 97/120，合计 194/240（80.83%）；3/12 个任务达到 20/20。46 个失败 seed 中 24 个为 expert 前检失败，22 个为 expert 通过但策略 0/5，没有 1-4/5 中间态。相较同一批任务旧清单的 181/240（75.42%），净增加 13 个成功 seed，即提高 5.42 个百分点；但 9/12 个任务仍低于 90%。完整逐任务表已写入 `summary.md`。 |
| 2026-08-30 00:07 | summary 统一大表维护 | 按用户要求重写 `summary.md`，不再分列原验证与重测结果。50 项表中 12 项使用重测结果直接替换旧行，37 项继续使用原验证，`put_object_cabinet` 使用补验；统一重算为 clean 461/500、random 456/500、合计 917/1000（91.70%），其中 22/50 项为 20/20。`open_microwave` 暂保留旧验证 10/20，状态标为“旧验证；重搜未完成”；00:07 快照时搜索仍为 `running`，clean 已找到 10 个、random 找到 8 个严格 5/5 seed，尚无最终 YAML 或新验证。旧表外单列的 12 项重测章节已移除。 |
| 2026-08-30 01:05 | `open_microwave` 重搜完成与产物审计 | SQLite 为 `completed`、exit code 0、`error_text` 为空，运行时间为 2026-08-29 15:00:47 至 2026-08-30 01:00:02；混合批次 14/14 项均已完成，原 launcher PID `525474`、调度器和搜索进程均已退出，GPU `0–7` 空闲。clean 尝试 54 个候选、random 尝试 66 个候选，各选出 10 个唯一 seed；20 个入选项均 expert 前检通过且策略严格 5/5，两个 phase 之间也不重复。最终 YAML、JSON summary 与 120 行候选 CSV 一致，没有 1-4/5 候选。该搜索产物可用于后续归档和独立验证，但当前未替换稳定清单、未提交新验证，因此 `summary.md` 仍保留旧验证 10/20，总体仍为 917/1000。 |
| 2026-08-30 01:11 | `open_microwave` 新清单归档与并行验证配置 | 按用户确认，将审计通过的最终 YAML 替换到稳定 successful-seeds 归档，归档文件与搜索产物 SHA256 均为 `9af15327ef6ca4a3c9839f40af014544d8413982d4536691ea6c70a271e83b36`。新增 `open-microwave-refreshed-validation-jobs.json`：一个通用调度作业调用现有验证器，验证器原生使用 GPU `0–7` 各一个 worker 并行消费 20 个 seed；worker 只写各自日志，唯一父进程写逐 seed JSON 和最终 summary，不存在并发写同一文件。通用调度器每个 job 只能在 SQLite 记录一个启动 GPU，不能表达单 job 多 GPU 资源，因此该一次性批次必须独占 GPU `0–7` 且不混入其他作业。此时尚未 dry-run 或正式提交。 |
| 2026-08-30 01:11 | 并行验证静态检查与 dry-run | 调度器和验证器 `py_compile`、归档哈希及 `git diff --check` 通过；归档 manifest 为 clean/random 各 10 个唯一 seed，跨 phase 无重复。临时 dry-run 在 `/tmp/fastwam-open-microwave-validation-dry-run.GgPRuv/output/` 生成恰好一个 queued 作业，命令固定传入 GPU `0–7`、输出路径保留独占 `{output_dir}`，没有启动子进程；policy 软链接仍指向预期实现。正式任务尚未提交。 |
| 2026-08-30 01:12 | `open_microwave` 并行验证提交与启动核验 | 提交前未发现调度器、搜索器、验证器或 GPU compute 进程，GPU `0–7` 均为 0 MiB、利用率 0%，磁盘剩余约 13 TiB。使用普通 `nohup + setsid` 启动一次性通用调度器，不使用 systemd；launcher PID `977753` 的 PPID 已变为 1，SID/PGID 均为 `977753`。SQLite 中唯一作业 `open_microwave_refreshed` 为 `running`、无错误，01:12:39 启动；其命令和验证器 run config 明确使用 GPU `0–7`，8 份独立 worker 日志均已创建，唯一任务输出目录为 `jobs/open_microwave_refreshed/`。结果根目录为 `evaluate_results/robotwin/seed_validation/open_microwave_refreshed_20260830_0112/`；本行只证明任务已正确启动，不表示验证成功，此后不持续监控。 |
| 2026-08-30 22:31 | `open_microwave` 验证完成、产物审计与 summary 替换 | SQLite 显示唯一作业于 01:26:14 `completed`、exit code 0、`error_text` 为空；launcher PID `977753`、作业 PID `977757` 及对应进程组均已退出，GPU `0–7` 空闲。20 份逐 seed JSON、8 份 worker 日志、run config、CSV 和 JSON summary 齐全，manifest、JSON、CSV 与 summary 三层重算一致。固定分母结果为 clean 8/10、random 6/10、合计 14/20（70.00%）：3 个 seed 因 `target_pose` 断言未通过 expert 前检，3 个 expert 通过但策略 0/5，没有 1-4/5。无调度失败、超时、OOM、CUDA 错误、traceback、native crash、进程被杀或磁盘写满；只有非致命 Vulkan fallback 与 `missing pytorch3d`。已用 14/20 直接替换统一大表旧行，总体由 917/1000 更新为 921/1000（92.10%）。本批未生成外部 `.launcher.pid` 文件，PID 证据来自提交账本与 SQLite started event；该元数据缺口不影响结果有效性。 |
| 2026-08-30 22:59 | 全范围终态口径与归档复核 | 复核稳定 `successful-seeds/` 恰有 50 份唯一任务 YAML，每份 clean/random 各 10 个唯一 seed且均记录 5 次连续成功；任务集合与 `summary.md` 的 50 行完全一致。13 项后续重搜产物均与同名稳定归档逐文件 SHA256 一致，`open_microwave.yaml` 已在前次验证提交前完成替换，因此本次无需重复写入。50 项当前采用的测试来源均已完成且 exit code 0；统一口径更新为“50/50 项已完成搜索归档与独立测试，40/50（80%）达到至少 90%，其中 22/50 达到 100%”，总体仍为 921/1000（92.10%）。 |

## 运行项

当前没有运行项。`open_microwave_refreshed` 已完成，launcher、调度器、验证器及 worker 进程均已退出；2026-08-30 22:31 检查时
GPU `0–7` 显存占用与利用率均为 0。

## 失败项与资源问题

首次正式承载尝试因用户不希望使用 systemd 而主动取消，不是验证器失败：49 项均为 `cancelled`，0 份 summary，无残留进程。正式重提批次未发生调度失败、超时、OOM、CUDA 错误、traceback、native crash、进程被杀或磁盘写满。

验证层共有 94 个未严格复现的 seed：60 个在 expert 前检失败，具体为 51 次 `expert planning did not reach task success`、5 次
`open_microwave` 的 `AssertionError: target_pose cannot be None for move action.`、4 次 `UnStableError`；另 34 个 expert 通过的
seed 在策略执行时均为 0/5。49 份 worker 日志均出现 SAPIEN 找不到 system Vulkan 后回退 builtin 的提示和 `missing pytorch3d`
提示，但所有 worker 均 model ready 且作业正常退出；`dump_bin_bigbin` 与 `put_bottles_dustbin` 另有 clutter 对象数量警告，未导致作业失败。

12 项重搜 seed 验证没有调度失败、超时、OOM、CUDA 错误、traceback、native crash、进程被杀或磁盘写满。该批 46 个失败 seed 中，
24 个错误均为 `expert planning did not reach task success`，其余 22 个通过 expert 后策略为 0/5；两类都按固定分母计为失败。所有 worker
仍有非致命的 Vulkan fallback 和 `missing pytorch3d` 提示；`dump_bin_bigbin` 另有 clutter 对象数量警告，但该任务本轮为 20/20。

`open_microwave` 并行验证没有调度或基础设施故障。其 6 个失败 seed 中，3 个因
`AssertionError: target_pose cannot be None for move action.` 未通过 expert 前检，另 3 个 expert 通过但策略为 0/5；两类都按固定分母计为
失败。8 份 worker 日志仅有非致命 Vulkan fallback 与 `missing pytorch3d` 提示。

按 `summary.md` 当前单一大表的最新结果，1000 个 seed 中共有 79 个失败：44 个 expert 前检失败，35 个 expert 通过但策略 0/5；
没有 1-4/5 中间态。该统计已经用 13 项重测替换对应旧行并加入 `put_object_cabinet`。

## 关键决策

- 本批次固定为现有 49 份已归档清单，不等待仍未归档的 `put_object_cabinet`，也不重新搜索环境 seed。
- 使用现有验证脚本和一次性 SQLite 调度器；验证作为普通 argv 作业提交，调度器不包含搜索或验证分支。本阶段不实现追加实验、追加任务、常驻 consumer、自动恢复或自动重试。
- SQLite 持久化单个调度器批次的状态和事件，但不是跨进程 GPU 锁；既然本阶段已取消追加/常驻设计，正式验证期间不得再启动另一个使用 GPU `0–7` 的同类调度器。
- 承载方式改为普通的脱离终端后台进程；不再使用或保留 systemd unit。以独立 PID、SQLite 和调度日志完成一次性审计。
- 使用 GPU `0–7`，每卡最多两个任务；单任务墙钟上限为 10 小时。正式提交时仍依据即时 GPU 状态确认资源可用性。
- 每个任务独占结果目录、launcher 日志和验证器 worker 日志；SQLite 与调度器日志由单个调度进程写入，禁止多个任务向同一文件并发追加。
- 正式运行使用独立实验名、SQLite 和结果根目录。提交后只核验一次队列与 GPU 分配并更新账本，此后不持续监控。
- 验证结果以 seed 为统计单位：每个任务固定 20 个 seed，只有 expert 前检通过且策略 5/5 的 seed 计为成功；expert 前检失败也直接计为 seed 失败，不从分母排除。保留 clean/random 分项及失败阶段分类用于诊断。
- 扩展批次把第 50 项验证与 13 项低成功率任务重搜作为普通 argv 混合提交到同一个通用调度器；使用 GPU `0–7`、每卡最多 2 项，不为此修改调度器业务逻辑。
- 完成重搜的 13 份清单按用户后续指示替换稳定归档，并已完成独立验证；其结果已经直接替换 `summary.md` 统一大表中的旧行。
- 18:32 启动的归档验证阶段曾以互斥 GPU 池隔离两个一次性调度器：旧搜索只占 GPU 6，新验证只声明 GPU `0,1,2,3,4,5,7`；该阶段现已结束。
- `summary.md` 只维护一张 50 任务最新结果表。后续某任务完成新验证时直接替换该行并重算总体统计，不再保留一张旧表和一张重测表；未完成新验证的任务继续显示上一次已完成结果，并在状态列明确说明。
- `open_microwave` 最终独立验证采用验证器原生多 GPU worker，而不是并发启动多个完整 manifest 作业；8 个 worker 各自写独立日志，唯一父进程写逐 seed JSON 和最终 summary。由于通用调度器当前只记录单 job 的一个启动 GPU，本次以一次性独占批次保证 GPU `0–7` 不与其他调度器重叠。

## 产物位置

- 任务书：[plan.md](plan.md)
- 账本：本文件。
- 总结：[summary.md](summary.md)。
- 通用作业清单：`validation-jobs.json`。
- 扩展阶段混合作业清单：`refresh-jobs.json`。
- 重搜 seed 验证作业清单：`refreshed-seed-validation-jobs.json`。
- `open_microwave` 并行验证作业清单：`open-microwave-refreshed-validation-jobs.json`。
- 清单来源：`../2026-08-27-robotwin-all-tasks-seed-search/successful-seeds/`。
- 已取消的首次 SQLite：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0203/scheduler.sqlite3`。
- 已取消的首次结果根目录：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0203/`；其中 49 项均为 `cancelled`，不得与后续正式重提结果合并。
- 正式重提结果根目录：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0207/`。
- 正式重提 SQLite：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0207/scheduler.sqlite3`。
- 后台 launcher PID/日志：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0207.launcher.pid` 与同名 `.launcher.log`。
- 扩展阶段结果根目录：`evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/`。
- 扩展阶段 SQLite：上述目录中的 `scheduler.sqlite3`。
- 扩展阶段 launcher PID/日志：同名结果根目录外的 `.launcher.pid` 与 `.launcher.log`。
- 重搜 seed 验证结果根目录：`evaluate_results/robotwin/seed_validation/refreshed_successful_seeds_12_20260829_1833/`。
- 重搜 seed 验证 SQLite：上述目录中的 `scheduler.sqlite3`。
- 重搜 seed 验证 launcher PID/日志：同名结果根目录外的 `.launcher.pid` 与 `.launcher.log`；提交时 PID 为 `738136`。
- `open_microwave` 并行验证结果根目录：`evaluate_results/robotwin/seed_validation/open_microwave_refreshed_20260830_0112/`。
- `open_microwave` 并行验证 SQLite 与日志：上述目录中的 `scheduler.sqlite3`、`scheduler.log`、`launcher_logs/open_microwave_refreshed.log`，以及根目录外的同名 `.launcher.log`；提交时 launcher PID 为 `977753`。该批没有外部 `.launcher.pid` 文件。

## 下一步

1. 当前没有待审计或运行中的任务，不自动重试失败 seed。
2. 若进一步研究重搜清单的复现性，继续区分 expert 前检失败与策略 0/5；`open_microwave` 本轮两类各 3 个，最终成功率仍只有 70.00%。
