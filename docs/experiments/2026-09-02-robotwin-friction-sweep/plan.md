# RoboTwin 全任务摩擦参数扫描计划

## 目标

在固定 FastWAM 权重和已归档 successful seeds 上，研究 RoboTwin 声明物理材质的摩擦系数变化对 50 个任务成功率的影响。

## 实验协议

- 分支：`successful-range`。
- checkpoint：`checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt`。
- policy seed：沿用每份归档 YAML 中的 `42`。
- 环境 seed：每个任务的 clean/random 分别取归档列表前三项。
- 摩擦值：`0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95`。
- 每个值同时设置 `static_friction` 和 `dynamic_friction`；只改变 RoboTwin 的 `scene.default_physical_material`，restitution 和 SAPIEN 其他默认材质不变。
- 每个任务、phase、摩擦值和环境 seed 执行一次策略 rollout。专家前检失败直接计为失败，不重试。
- 总规模：$50 \times 2 \times 7 \times 3 = 2100$ 次策略 rollout 槽位。

## 调度与产物

- 使用一次性 SQLite 调度器，只使用 GPU `0–4`，每卡最多同时运行两个任务，最多 10 个并发任务。
- 每个任务独占输出目录和 launcher 日志；原始结果写入 `evaluate_results/robotwin/friction_sweep/`。
- 每个任务生成 clean/random 两张曲线图；稳定文档引用的图片归档到本目录 `images/`。
- 最终 `summary.md` 汇总逐任务平均成功率，以及每个摩擦值下 clean、random 和合并总体成功率。

## 成功标准

- 50 个任务均生成 42 条完整记录，共 2100 条。
- 每个 task/phase/friction 单元固定以 3 个 seed 为分母。
- 汇总表、图和原始 JSON/CSV 统计一致。

