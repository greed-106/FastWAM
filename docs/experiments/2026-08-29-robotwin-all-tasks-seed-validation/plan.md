# RoboTwin 全任务 Successful Seeds 验证任务书

## 目标

本阶段复测稳定归档目录
`docs/experiments/2026-08-27-robotwin-all-tasks-seed-search/successful-seeds/`
中的 49 份任务清单，检验搜索得到的环境 seed 在同一验证协议下能否再次成功。44 份清单来自此前已经完成的任务，另纳入本次新增的
`move_stapler_pad`、`open_laptop`、`place_mouse_pad`、`place_object_scale` 和
`stamp_seal`。

每份清单包含 clean 与 random 两个阶段，每阶段各 10 个环境 seed；每个 seed 按清单中的
`consecutive_successes: 5` 独立执行 5 次策略 rollout。因此本批次共验证 49 个任务、980 个环境 seed、4900 次 rollout。
本实验验证固定清单的复现性，不重新搜索 seed，也不把尚未归档的 `put_object_cabinet` 纳入本批次。

## 固定验证协议

| 项目 | 设定 |
| --- | --- |
| 清单来源 | `docs/experiments/2026-08-27-robotwin-all-tasks-seed-search/successful-seeds/<task>.yaml` |
| 策略与权重 | 清单中的 `fastwam_policy` 发布权重；当前 49 份均指向 `checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt` |
| 策略采样 seed | 使用各清单的 `policy_seed`；当前 49 份均为 `42` |
| 阶段 | clean：`demo_clean` + `seen`；random：`demo_randomized` + `unseen` |
| 每任务规模 | 20 个环境 seed，每个执行 5 次，共 100 次 rollout |
| 总规模 | 49 个任务、980 个环境 seed、4900 次 rollout |
| GPU | GPU `0–7`，每张 GPU 同时最多运行两个任务 |
| 单任务墙钟上限 | 10 小时；超时后终止该任务，不自动重试 |

验证严格读取清单中每个 seed 自身的 `consecutive_successes`，不修改环境 seed、策略 seed、推理参数或成功判定。每次 rollout
仍执行独立环境重置；验证器沿用 seed-search 已修复的候选级任务实例生命周期，使专家阶段建立的派生状态可供该 seed 的 rollout 使用。

## 实施与调度

复用 `experiments/robotwin/validate_robotwin_successful_seeds.py` 执行单任务验证。一次性 SQLite 调度器不包含搜索或验证模式；
`validation-jobs.json` 通过通用 `--jobs-file` 接口提交 argv 数组。其顶层 `argv_template` 使用 `{job_name}` 定位 `<task>.yaml`，并将
单张 `{gpu_id}` 和独立 `{output_dir}` 传给验证器。调度器仅负责 SQLite 状态、FIFO、GPU 槽位、超时、进程组和 launcher 日志；原有
`--task-names` seed-search 调用继续兼容。

调度器一次性写入本实验的 49 个任务，按照 FIFO 向 GPU `0–7` 的空闲槽位动态派发；每卡容量为 2，共 16 个任务槽位。
任务结束后，同一卡释放的槽位继续消费本实验剩余队列。队列没有待运行或运行中任务时，调度器正常退出；本阶段不增加任务追加、常驻 consumer、自动恢复或失败重试能力。

并发写入按以下方式隔离：

- 每个任务写入结果根目录下独立的 `jobs/<task>/` 目录；
- 每个任务使用独立的 `launcher_logs/<task>.log`；
- 验证器在任务目录内维护自己的 worker 日志、逐 seed JSON、`summary.json` 和 `summary.csv`；
- SQLite 与 `scheduler.log` 只由单个调度器进程写入，不由任务进程并发追加；
- 启动调度器前单进程调用现有 helper 创建并核验 RoboTwin 的 `fastwam_policy` 软链接，避免首批任务竞争创建同一路径；该动作不属于通用调度器职责。

正式运行使用独立的实验名、SQLite 文件和结果根目录，不复用 seed 搜索队列或历史结果目录。提交前重新检查现有队列、相关进程和 GPU
占用，禁止重复提交已经成功的同批验证任务。

## 验证、提交与完成标准

提交前完成以下检查：

1. 加载全部 49 份 YAML，确认文件名与 `task_name` 一致、clean/random 各含 10 个唯一 seed、每个 seed 复测次数为 5，且 checkpoint、策略 seed 与阶段配置一致。
2. 检查 RoboTwin 任务资产和 checkpoint 存在，执行调度器与验证器的 `py_compile` 和 `--help`。
3. 使用临时结果根目录执行通用 jobs-file dry-run，确认 49 个任务无遗漏、无重复，渲染命令指向正确 manifest/GPU/输出目录，且每个任务的日志与结果路径相互独立。
4. 正式提交前再次查询相关进程、已有结果和 GPU 当前状态；仅在确认没有相同验证任务后启动一次性调度器。
5. 通过普通脱离终端后台进程提交，并只做一次启动核验：确认 SQLite 中 49 个任务均进入 `queued` 或 `running`，运行任务使用 GPU `0–7` 且每卡不超过两个，并记录调度器 PID、SQLite、结果根目录和状态。不使用 systemd service；此后按用户要求不持续监控。

后续恢复检查时，以各任务 `summary.json` 汇总：4900 次 rollout 中的成功次数、980 个 seed 中完成全部 5 次成功的数量、clean/random
各自结果，以及 49 个任务中全部 seed 均通过的任务数。子进程非零退出、超时、专家规划失败和部分 rollout 失败必须分别如实报告；不得把队列提交或进程启动表述为验证成功。所有任务进入终态并完成产物审计后再创建 `summary.md`。

## 扩展阶段：第 50 项验证与低成功率任务重搜

在原 49 项验证完成后，稳定归档新增了 `put_object_cabinet.yaml`。本扩展阶段使用现有验证器复测其中 20 个环境 seed，使验证范围补齐到
50 个任务；同时按照现有 `summary.md` 的固定口径，选取测试成功率严格低于 90% 的 13 个既有任务重新执行 successful-seeds 搜索。
恰好 90% 的任务不纳入重搜。

本阶段通过 `refresh-jobs.json` 向同一个通用 SQLite 调度器混合提交 14 项普通 argv 作业：1 项
`validate_put_object_cabinet` 和 13 项 seed search。搜索仍使用 clean/random、base/policy seed `42`、默认环境 seed 起点 `4300000`、
每阶段最多 1000 个候选、目标 10 个 seed、每候选 5 次 rollout 以及同一发布 checkpoint；不调整模型推理参数。GPU 使用 `0–7`，
每卡最多两个作业，单作业超时 10 小时。

重搜结果写入新的独立结果根目录，不覆盖稳定归档中的现有 YAML。搜索作业 exit code 0 也不自动视为搜索成功；只有 clean/random
各产生 10 个唯一且严格 5/5 的 seed，并经 YAML、summary 与逐候选结果一致性审计后，才能表述为完成。新搜索得到的 seed 未经独立
验证前，不用于改写原验证成功率。

第 50 项与 13 项搜索立即混合提交。若 `put_object_cabinet` 后续验证成功率也低于 90%，待本批完成审计时再通过全局调度器建立独立
单任务搜索批次；一次性 SQLite 队列不增加追加或常驻模式。本批仍以普通 `nohup + setsid` 后台进程承载，不使用 systemd，只做一次
启动核验，此后不持续监控。

## 扩展阶段：重搜 seed 归档与独立验证

13 个低成功率任务中，除仍在 GPU 6 搜索的 `open_microwave` 外，其余 12 个任务已产生 clean/random 各 10 个严格 5/5 的新 seed。
先以这 12 份新清单替换稳定实验目录内的同名 YAML，再通过 `refreshed-seed-validation-jobs.json` 让现有验证器读取替换后的稳定归档；
验证结果写入全新的结果目录，不覆盖旧验证结果或重搜原始产物。

新开一个独立的一次性 SQLite 调度器，只声明 GPU `0,1,2,3,4,5,7`，明确排除 GPU 6；每张卡同时最多运行两个验证作业。12 个任务
各自使用独立的 `jobs/<task>/` 输出目录、launcher 日志和 worker 日志。调度器仍以普通 `nohup + setsid` 后台进程承载，不使用
systemd；提交前执行静态检查、清单审计和临时 SQLite dry-run，正式提交后只做一次启动核验。

最终统计继续使用唯一口径：每任务固定 20 个 seed，clean/random 各 10 个；只有本次 expert 前检通过且策略 5/5 的 seed 才成功，
expert 前检失败直接计为该 seed 失败。逐任务报告 clean、random、成功 seed/20、测试成功率、expert 前检失败数和 expert 通过但策略
失败数；新验证结果单独呈现，不静默覆盖原 49 项表格。
