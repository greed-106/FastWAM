# RobotWin `click_bell` 高成功率 Seed 搜索实验总结

## 结论

在保持 FastWAM/RoboTwin 默认外部 base seed `42` 的条件下，本实验已分别为 clean 和 random 阶段找到 10 个高质量环境 seed：

`4300000, 4300001, 4300002, 4300003, 4300004, 4300005, 4300006, 4300007, 4300008, 4300009`。

每个入选 seed 都通过专家可行性筛选，并在对应阶段完成 5/5 次策略 rollout 成功。clean 使用本实验显式设定的 `seen` 指令，random 使用 `unseen` 指令。

机器可读清单已写入 `evaluate_results/robotwin/seed_search/click_bell_seed42_clean_random_20260826/successful-seeds.yaml`。它仅记录跨服务器复测所需的任务、相对权重路径、策略采样 seed、复测次数、阶段配置及入选环境 seed。

## 实际执行

使用发布权重 `robotwin_uncond_3cam_384.pt`，在 GPU 2、3、4、5 上并行搜索。外部 base seed `42` 按 RoboTwin 的默认规则给出首个环境 seed `4300000`；候选环境 seed 之后连续递增，搜索上限设为 1000。

| 阶段 | 实际完成候选数 | 专家筛选失败 | 专家通过后的策略失败 | 5/5 成功记录 | 入选数量 |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 11 | 0 | 0 | 11 | 10 |
| random | 12 | 2 | 0 | 10 | 10 |

两个 random 未通过专家筛选的候选是 `4300010` 和 `4300011`，分别因为随机桌面物体 `065_soy-sauce`、`088_wineglass` 不稳定；它们没有进入策略 rollout，不能归类为策略失败。阶段达到 10 个入选 seed 后，少量已在运行的候选仍会完成，因此 clean 比目标多出 1 条 5/5 成功记录。

## 实现与验证

新增 `experiments/robotwin/search_robotwin_seeds.py`，参数化任务、阶段、GPU、base seed、候选上限、目标数量、复测次数、权重和主要 FastWAM 推理参数。每张 GPU 使用一个持久模型 worker；结果逐候选写入 JSON，并在结束时生成 JSON/CSV 汇总及 `successful-seeds.yaml`。后者仅收录已入选且 5/5 成功的环境 seed，并保留跨服务器复测所需的最小参数集。

正式搜索的数据结果全部落盘且经逐记录核验。收尾时发现主进程把已报告完成的正常 worker 误判为异常退出，导致该次命令返回非零；这不影响候选结果。修复后，以两个 worker、一个候选的针对性 smoke test 验证了“一个 worker 先正常退出、另一个完成任务”的收尾路径，退出码为 0。

本阶段的验证包括：脚本编译、命令行帮助、单 worker smoke test、双 worker 收尾 smoke test，以及对正式结果中 20 个入选记录的直接断言。后者确认每条记录的专家结果为真、base/policy seed 均为 `42`、阶段语言设定正确，且恰有 5 条成功 rollout。

## 局限与后续方向

- 本实验寻找的是满足严格 5/5 条件的可复现 seed，不是该任务的总体成功率估计；达到每阶段 10 个目标后即停止搜索。
- 同一外部 base seed 同时固定了 FastWAM 的策略采样 seed。FastWAM 每次动作推理都会以该值新建 `torch.Generator` 并生成扩散动作初始噪声；它不改变本实验单独传入 `setup_demo` 的环境 seed。因此 5 次 rollout 证明固定策略采样 seed 下端到端独立重置/执行的成功稳定性，但不证明覆盖了五种不同的模型随机采样。若要检验采样噪声鲁棒性，应另建实验，将环境 seed 与策略采样 seed 显式拆分并预先固定一组策略 seed。
- clean=`seen`、random=`unseen` 是本实验显式选择的阶段协议，不是现有通用评测入口自动执行的映射。若需要语言条件的公平对照，应显式传入统一的 `--instruction-type` 后另建实验项目。

## 主要产物

- 正式运行配置与逐候选结果：`evaluate_results/robotwin/seed_search/click_bell_seed42_clean_random_20260826/`
- 成功 seed 清单：`evaluate_results/robotwin/seed_search/click_bell_seed42_clean_random_20260826/successful-seeds.yaml`（SHA256：`d697d2aee071959838259a67a6833b30a8435ee0769e66cffe1d549ced13f9b5`）。
- 正式汇总：`summary.json`、`summary.csv`（SHA256 分别为 `0d0738fbf8eba493bb205fd770e195c1118e4559e5aa2e0c9bed62f095162973`、`0e8d8649c0d3d56dcb8f78553cf82420429ce6beadae9e7aaffe90d0e71bc709`）。
- 当前搜索脚本 SHA256：`aba6825227fdef53fe1f85a3d5922f42280c444dc9e000fa12c12dd9e1eeada2`。
