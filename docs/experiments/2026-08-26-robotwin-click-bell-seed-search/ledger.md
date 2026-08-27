# RobotWin `click_bell` 高成功率 Seed 搜索主账本

## 实验标识

- 稳定项目目录：`docs/experiments/2026-08-26-robotwin-click-bell-seed-search/`
- 启动日期：2026-08-26
- 当前状态：原 seed 搜索阶段与跨服务器固定 seed 复现实验均已完成；两阶段全部 20 个指定 seed 均为 5/5 成功。
- 任务书：[plan.md](plan.md)

## 目标

在 RoboTwin `click_bell` 任务中，分别为 clean 和 random 阶段从至多 1000 个连续候选环境 seed 中各找出 10 个高质量 seed。每个高质量 seed 必须在对应阶段完成 5/5 次策略 rollout 成功。默认使用 GPU 2、3、4、5、外部 base seed `42` 和发布权重 `checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt`，但所有关键参数必须由脚本参数配置。

## 当前代码支持

- `experiments/robotwin/eval_robotwin_single.py` 可把 Hydra 的 `seed`、任务名、阶段配置、GPU 与 FastWAM 推理参数传给 RoboTwin 单任务评测入口。
- FastWAM 默认外部 seed 是 `42`；`third_party/RoboTwin/script/eval_policy.py` 从 $\mathrm{environment\_seed}=100000\times(1+s)$ 开始，其中 $s$ 是该外部 base seed，之后逐个递增环境 seed。
- 上游评测会自动跳过专家规划失败的环境，直至凑满 episode 数；它不支持有界连续环境 seed 枚举、精确单环境 seed 测试、每 seed 5 次复测或显式 GPU 列表。
- `experiments/robotwin/run_robotwin_manager.py` 支持 clean/random 阶段串联，但当前只会使用从 GPU 0 开始的连续编号，不能满足默认 GPU `2,3,4,5` 的要求。
- 新增 `experiments/robotwin/search_robotwin_seeds.py`：显式接收任务、阶段、物理 GPU、base seed、候选上限、目标数量、复测次数、权重和推理参数；每 GPU 保持一个已加载模型的 worker，并逐候选保存 JSON、汇总 JSON/CSV、`successful-seeds.yaml` 和 worker 日志。它按本实验协议显式将 clean 映射为 `seen`、random 映射为 `unseen`，默认关闭评测视频写入。
- 新增 `experiments/robotwin/validate_robotwin_successful_seeds.py`：读取成功 seed YAML，严格使用其中的任务、权重、固定策略采样 seed、复测次数、阶段配置与环境 seed，在不重新搜索或偏移 seed 的前提下并行输出每个 seed 的成功率。

以上为当前代码能力描述，不代表本阶段已经执行、删除或验证任何策略。

## 本阶段实际执行

| 时间（Asia/Shanghai） | 事项 | 结果与证据 |
| --- | --- | --- |
| 2026-08-26 | 启动实验项目并创建稳定目录 | 新建本目录、任务书和主账本；尚未修改评测代码。 |
| 2026-08-26 | 工作树检查 | 仅发现用户提供的未跟踪 `AGENTS.md`；未修改、未覆盖。 |
| 2026-08-26 | 调度与历史结果检查 | 未发现 `squeue`、`sbatch`、`qstat` 或 `bjobs`；无 RobotWin/FastWAM 评测进程，未发现已有 `click_bell` 结果。 |
| 2026-08-26 | GPU 状态检查 | GPU 2、3、4、5 均空闲；GPU 0、1、6、7 正被其他项目使用，未触碰。 |
| 2026-08-26 | seed 语义审计与文档更正 | 确认默认外部 seed 为 `42`，上游从环境 seed `4300000` 开始并连续递增；任务书和本账本已据此更正，尚未修改评测代码。 |
| 2026-08-26 | 实现专用搜索脚本 | 新增 `experiments/robotwin/search_robotwin_seeds.py`；实现四卡持久 worker、1000 个连续环境 seed 上限、每候选 5 次 rollout、阶段独立的 10 个目标及 JSON/CSV 结果。未启动仿真。 |
| 2026-08-26 | 静态检查 | `uv run --no-sync python -m py_compile experiments/robotwin/search_robotwin_seeds.py` 和脚本 `--help` 均通过。 |
| 2026-08-26 23:00 +08:00 | 提交 smoke test | 以 GPU 2、clean、base seed `42`、`max_seed_attempts=1`、`target_good_seeds=1`、`repeats=1` 启动专用脚本。运行目录：`evaluate_results/robotwin/seed_search/click_bell_20260826_230053/`。 |
| 2026-08-26 23:03 +08:00 | smoke test 完成 | clean 环境 seed `4300000` 的专家检查通过，1/1 策略 rollout 成功（54 步）；汇总与逐候选 JSON/CSV 已生成。 |
| 2026-08-26 23:03 +08:00 | 提交正式搜索 | 使用 GPU `2,3,4,5`、阶段 `clean,random`、base seed `42`、连续环境 seed `4300000…4300999`、每阶段目标 10、每候选 5 次 rollout 启动专用脚本。运行目录：`evaluate_results/robotwin/seed_search/click_bell_seed42_clean_random_20260826/`。 |
| 2026-08-26 23:17 +08:00 | 阶段目标达成 | clean 入选 `4300000…4300009`；random 入选同一组 10 个环境 seed。每个入选记录均有 5 次成功 rollout。 |
| 2026-08-26 23:18 +08:00 | 正式搜索收尾失败 | 所有目标结果已写入后，worker 正常以 exit code 0 退出；主进程在读取最后完成消息前将其误判为失败并返回非零。未重跑，保留结果与日志，准备一次最小修复。 |
| 2026-08-26 23:24 +08:00 | 提交收尾修复验证 | 修复仅排除已报告 `done` 的正常 worker；以 GPU 2、3、clean、1 个环境 seed、1 次 rollout 启动双 worker smoke test。运行目录：`evaluate_results/robotwin/seed_search/click_bell_multiworker_smoke_20260826/`。 |
| 2026-08-26 23:26 +08:00 | 收尾修复验证完成 | GPU 2 先正常退出，GPU 3 完成唯一候选后正常收尾，命令退出码为 0。 |
| 2026-08-26 | 正式结果核验与总结 | 直接核验 clean/random 各 10 条入选记录均为专家通过、base/policy seed `42`、5/5 rollout 成功；新增 [summary.md](summary.md)。 |
| 2026-08-27 | 增加成功 seed 清单 | 搜索脚本在结束时生成 `successful-seeds.yaml`，仅收录已入选且全部 rollout 成功的记录；已由正式结果回填该文件，未重新启动 GPU 仿真。 |
| 2026-08-27 | 跨服务器校验脚本与静态检查 | 新增 YAML 驱动的固定 seed 校验入口；`py_compile`、`--help` 与成功 YAML 加载断言均通过。计划以 GPU `0,1,2,3,4,5,6,7` 对 clean/random 各 10 个 seed 分别运行 5 次，不添加 seed 偏移。 |
| 2026-08-27 01:15 +08:00 | 跨服务器固定 seed 正式校验完成 | 使用全部 8 张 GPU 读取 `click-bell-successful-seeds.yaml`，直接测试 clean/random 各 10 个环境 seed、每 seed 5 次 rollout。两阶段均为 10 个专家通过 seed、50/50 rollout 成功；全部逐 seed 成功率为 100%。 |

## 完成项

- [x] 阅读项目协作规范并核对工作树、调度器状态和既有结果。
- [x] 建立稳定实验目录。
- [x] 建立中文任务书，锁定任务、两阶段目标、5/5 判定、1000 连续候选环境 seed 上限、GPU 与默认 seed 语义。
- [x] 建立主账本并记录初始环境状态。
- [x] 实现可配置、有界的 seed 搜索调度器。
- [x] 完成单 seed smoke test。
- [x] 提交并完成 4-GPU 正式搜索的数据采集与结果核验。
- [x] 写入最终实验总结。
- [x] 生成机器可读的成功 seed 清单，并记录固定策略采样 seed 与 5/5 判定条件。
- [x] 实现并静态验证 YAML 驱动的跨服务器固定 seed 校验入口。
- [x] 完成跨服务器固定 seed 正式校验并核验 20 条逐 seed 结果。

## 运行项

当前无运行中的本实验任务。

## 失败项与资源问题

外部批处理调度器命令在当前环境中不可用；这是一项环境事实，不是本实验任务失败。smoke test 日志出现 SAPIEN 使用内置 Vulkan 的提示以及 `missing pytorch3d` 文本，但退出码为 0、专家检查和 rollout 均成功，因此仅作为非阻塞环境提示记录。

正式搜索的收尾逻辑曾存在一处代码缺陷：正常 exit code 0 的 worker 在最后一条完成消息尚未被父进程读取时，被父进程误判为异常退出。该缺陷不影响已落盘的 23 个候选结果，也不改变两阶段均已达到 10 个 5/5 成功 seed 的事实。修复后已通过双 worker 针对性 smoke test。

random 阶段的环境 seed `4300010` 和 `4300011` 未通过专家筛选，原因分别是杂物 `065_soy-sauce`、`088_wineglass` 不稳定；两者都未进入策略 rollout，未计入策略失败。专用脚本使用仓库内的持久 worker 调度。

## 关键决策

- seed 保持上游默认语义：FastWAM 外部 base seed 默认是 `42`，上游起始环境 seed 为 `100000 × (1+42)=4300000`，之后连续递增。默认枚举 `4300000…4300999` 共 1000 个环境 seed，策略采样 seed 保持为 `42`。
- clean 与 random 分别各需要 10 个高质量 seed；不要求同一个逻辑 seed 同时通过两阶段。
- 每个候选在对应阶段共执行 5 次策略 rollout；只有 5/5 成功才入选。
- `successful-seeds.yaml` 仅记录跨服务器复测所需的任务、相对权重路径、策略采样 seed、每个 seed 的连续成功次数、每阶段任务配置/指令类型和入选环境 seed；可由这些信息推导或不影响复测的字段不重复保存。
- YAML 的单一 `policy_seed: 42` 表示 5 次 rollout 沿用同一个策略采样 seed；它们验证独立环境重置/执行的稳定性，不表示已经覆盖多种扩散采样噪声。
- 跨服务器校验直接把 YAML 中的 `successful_seeds` 传给 `setup_demo(seed=...)`；不从 `policy_seed` 重算环境 seed，也不因 GPU、worker 或重复次数添加偏移。
- 跨服务器复现通过条件是 clean 与 random 的全部 20 条 YAML 指定记录均为专家通过、策略 seed `42`、5/5 rollout 成功；本次结果满足该条件。
- clean=`seen`、random=`unseen` 是本实验显式实现的阶段语言映射；当前通用入口实际默认两个阶段都是 `unseen`。显式统一参数才覆盖本实验映射。
- 专家规划可行性检查与策略成功判定分开记录。专家失败或运行异常不应被写成策略失败成功率，也不能绕过 1000 候选上限。
- 正式搜索的选中顺序按结果到达主进程的顺序记录；并行中的额外候选可在阶段达标后完成，但不改变已选的前 10 个 seed。

## 产物位置

- 协议与参数定义：`docs/experiments/2026-08-26-robotwin-click-bell-seed-search/plan.md`
- 账本：本文件。
- 正式搜索结果与成功 seed 清单：`evaluate_results/robotwin/seed_search/click_bell_seed42_clean_random_20260826/`（其中 `successful-seeds.yaml` 已完成并核验）。
- smoke test 结果：`evaluate_results/robotwin/seed_search/click_bell_20260826_230053/`。
- 收尾修复 smoke test：`evaluate_results/robotwin/seed_search/click_bell_multiworker_smoke_20260826/`。
- 跨服务器校验结果：`evaluate_results/robotwin/seed_validation/click_bell_cross_server_20260827/`；`summary.json` SHA256 为 `1c0344c67c05f6d73fc036bf68c3e2af8bb37ee4a1118230ab85cebd354522d2`，`summary.csv` SHA256 为 `72b637dee1f2061d1eec160947294c99256a70eb14d88e949355ef07e5283132`。
- 实验总结：[summary.md](summary.md)。

## 下一步

本实验阶段无待执行项。后续若测试其他任务、权重、语言条件或策略采样 seed，应新建独立稳定实验目录，复用本脚本的显式参数并重新记录账本。
