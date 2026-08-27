# RobotWin `click_bell` 高成功率 Seed 搜索任务书

## 1. 研究目标

本实验在 RoboTwin 框架中评估 FastWAM 发布权重在 `click_bell` 任务上的环境 seed 稳健性。目标不是估计总体成功率，而是为后续可复现实验筛选出在固定初始环境下仍能稳定完成任务的 seed。

对 clean 与 random 两个阶段分别寻找 10 个高质量 seed。一个 seed 只有在该阶段的 5 次独立策略 rollout 全部成功时，才记为高质量 seed。这里的重复用于检验同一初始环境下的独立 rollout 稳健性；它不声称一定产生五种不同的模型采样结果。

## 2. 已确认的实验定义

| 项目 | 设定 |
| --- | --- |
| 任务 | `click_bell` |
| 策略 | `fastwam_policy` |
| 默认权重 | `checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt` |
| 阶段 | `clean`（`demo_clean`）与 `random`（`demo_randomized`） |
| 每阶段目标 | 10 个高质量 seed |
| 每个候选的策略复测次数 | 5 次，总数为 5 而非首次成功后再额外 5 次 |
| 通过条件 | 对应阶段的 5 次 rollout 均满足 `TASK_ENV.eval_success` |
| 外部 base seed | 默认 `42`，与当前 FastWAM 评测入口一致；可由脚本参数调整 |
| 候选环境 seed 范围 | 默认 `4300000` 至 `4300999`，共 1000 个连续 seed；由 base seed 和搜索上限确定 |
| GPU | 默认 `2,3,4,5`；可由脚本参数调整 |

### Seed 语义

本实验保留 FastWAM 与 RoboTwin 当前评测入口的默认 seed 行为。FastWAM 配置的默认外部 seed 为 `42`；上游 `third_party/RoboTwin/script/eval_policy.py` 首先将输入的 base seed $s$ 映射为：

$$
\mathrm{environment\_seed}=100000\times(1+s).
$$

上游随后在搜索过程中把环境 seed 每次加 `1`。因此，默认 `s=42` 的第一个环境 seed 是 `4300000`；本实验精确枚举连续的 1000 个环境 seed，即 `4300000` 至 `4300999`。专用工具不会沿用上游“自动跳过并继续寻找”的无界循环。

为保持同一入口的模型采样语义，策略采样 seed 在该次运行内保持为外部 base seed（默认 `42`），而候选环境 seed 独立递增。结果产物必须同时保存外部 base seed、实际环境 seed 和策略采样 seed，避免后续复现实验时产生歧义。

### 阶段与语言设置

`demo_clean.yml` 写有 `eval_instruction: seen`，并关闭背景、桌面杂物、光照和桌高随机化；`demo_randomized.yml` 写有 `eval_instruction: unseen`，并启用背景、杂物、光照和桌高随机化。上游评测代码并不会自动读取这两个 `eval_instruction` 字段，而是使用其 CLI `instruction_type` 参数。

根据本实验先前确认的阶段协议，专用搜索工具将**显式**设定 clean 为 `seen`、random 为 `unseen`；这不是当前通用入口的自动默认行为。用户显式传入统一的 `--instruction-type` 时才覆盖该映射。现有仓库通用评测配置 `configs/sim_robotwin.yaml` 默认将两个阶段都设为 `unseen`。

## 3. 实施方案

现有上游评测循环会从 `100000 × (1+s)` 开始递增环境 seed，并自动跳过专家规划失败的环境，直到收集到指定数量的 episode。它既不能限制候选集合为 1000 个逻辑 seed，也不能为同一环境 seed 保存 5 次独立 rollout 结果。因此本实验将新增独立的、有界 seed 搜索入口，而不改变上游通用评测的语义。

该入口应提供以下参数：

- `--task-name`：RoboTwin 任务名，默认 `click_bell`。
- `--phases`：阶段列表，默认 `clean,random`。
- `--gpu-ids`：可用 GPU 列表，默认 `2,3,4,5`。
- `--seed` 和 `--max-seed-attempts`：沿用 FastWAM 的外部 base seed 与连续候选环境 seed 数量，默认 `42` 和 `1000`。
- `--target-good-seeds`：每阶段目标数量，默认 `10`。
- `--repeats`：每个候选的策略 rollout 数量，默认 `5`。
- `--ckpt`：模型权重路径，默认上述发布权重。
- `--output-dir`：结果目录；未指定时在 `evaluate_results/robotwin/seed_search/` 下按时间创建新目录，已有非空目录不覆盖。
- 现有 FastWAM 推理参数及可选的统一 `--instruction-type` 覆盖。

每个阶段独立调度以下流程：

1. 从 $100000\times(1+s)$ 开始枚举尚未处理的连续环境 seed，严格不超出配置的候选数。
2. 用该阶段配置和对应环境 seed 进行专家规划可行性检查；不可行、初始化失败或执行错误都记录原因，并消耗一个候选环境 seed 名额。
3. 对通过可行性检查的候选，以相同环境 seed 重新初始化环境，执行 5 次策略 rollout，并逐次记录成功或失败。
4. 仅当 5 次全部成功时，写入该阶段的高质量 seed 列表；任一次失败即淘汰该候选。
5. 每个阶段达到 10 个高质量 seed 后停止分派该阶段的新候选；若 1000 个候选耗尽仍未达到目标，如实报告未达标数量。

四张 GPU 各运行一个持久 worker，由中心调度器动态分派 seed-阶段工作；每个 worker 只加载一次模型。每个候选完成后立即写入独立的结构化结果文件。为避免不透明地混合不同运行，已有结果目录默认不覆盖；中断后的重新执行使用新的输出目录。

seed 搜索默认关闭评测视频写入，以免大量候选消耗无关的磁盘空间；这不改变 `TASK_ENV.eval_success` 的判定。需要视频证据时，应使用普通单任务评测入口对已选 seed 单独复测。

## 4. 成功判定与产物

`click_bell` 的任务成功由 RoboTwin 的 `TASK_ENV.eval_success` 给出。任务实现还要求对应夹爪闭合，且夹爪与铃铛顶端接触位置在 XY 平面各小于 `0.025`、Z 方向小于 `0.03` 的容差内。脚本以 `TASK_ENV.eval_success` 作为每次策略 rollout 的唯一通过信号，不以日志文本或视频文件名替代。

每次运行在 `evaluate_results/robotwin/` 下建立独立运行目录，并至少产出：

- 生效参数和权重、配置、代码版本信息；
- 逐候选、逐次 rollout 的 JSON/CSV 记录，含阶段、外部 base seed、策略采样 seed、环境 seed、专家检查结果、成功结果、错误摘要、GPU 与日志路径；
- `successful-seeds.yaml`：仅收录已入选且所有 rollout 成功的 seed，并记录跨服务器复测所需的任务、相对权重路径、策略采样 seed、每个 seed 的连续成功次数、阶段任务配置和指令类型；
- clean 与 random 各自的运行汇总；
- worker 与调度器日志。

实验结束后，将上述产物路径、最终 seed 清单、成功/失败数量、资源异常和结论写入本目录的 `ledger.md` 与 `summary.md`。

## 5. 验证门槛与风险处理

实现完成后先进行 `--help` 与 Python 编译检查，再以单 GPU、单环境 seed、单阶段、单次 rollout 做 smoke test。只有 smoke test 成功后，才启动完整的 4-GPU 搜索。

如遇 OOM、磁盘写满、缺失权重或数据、CUDA/依赖不兼容、网络或仿真资源故障，立即把错误、日志和受影响 seed 记入 `ledger.md`；对明确代码缺陷或配置错误最多进行一次有依据的修复与验证。不得因资源错误反复重试、删除用户数据或把未执行阶段写为已完成。

## 6. 当前边界

截至任务书创建时，仓库尚未提供该专用搜索工具，尚未提交或运行本实验，也尚未生成任何 `click_bell` 搜索结果。本任务书描述的是已确认的实验协议和待实施工作，不是实验结果。
