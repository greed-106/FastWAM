# RoboTwin 全任务摩擦参数扫描账本

## 实验标识

- 稳定项目目录：`docs/experiments/2026-09-02-robotwin-friction-sweep/`
- 启动日期：2026-09-02
- 当前状态：50 项正式摩擦扫描已正常启动；10 项运行、40 项排队，GPU `0–4` 各运行两个任务。
- 任务书：[plan.md](plan.md)

## 目标

使用 50 份稳定 successful-seeds YAML 中 clean/random 各前三个环境 seed，扫描七个摩擦值，得到逐任务和全任务成功率曲线。

## 当前代码支持

- 现有 fixed-seed validator 可复用模型加载、专家前检和策略 rollout 逻辑，但尚不支持摩擦扫描。
- RoboTwin `Base_Task.setup_scene()` 声明的静摩擦和动摩擦默认值均为 `0.5`；当前 `_init_task_env_()` 未透传这两个参数。
- 通用 SQLite 调度器支持 JSON argv 作业、GPU 容量限制、超时和独立输出目录。

以上仅描述当前工程能力，不表示本阶段实验已经执行。

## 本阶段实际执行

| 时间（Asia/Shanghai） | 事项 | 结果与证据 |
| --- | --- | --- |
| 2026-09-02 | 启动前检查 | 已阅读 `AGENTS.md` 和上一阶段稳定账本；当前起点为 `find-successful-seeds` 的 `6ecfaac`，工作树干净。未发现 RoboTwin scheduler/search/validation/eval 进程，GPU `0–7` 均为 H100 80GB 且检查时空闲。现存旧 SQLite 无 queued/running 作业；未发现既有摩擦扫描结果。 |
| 2026-09-02 | 分支与协议确认 | 创建本地分支 `successful-range`。固定扫描值为 `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95`，静/动摩擦同步变化；clean/random 各取归档前三个 seed，每 seed 一次 rollout。正式批次只使用 GPU `0–4`，每卡最多两个任务。 |
| 2026-09-02 | 摩擦参数透传 | `_init_task_env_()` 现在把静/动摩擦显式传给 `setup_scene()`，默认仍为 `0.5`；评测参数构建仅在扫描配置包含对应字段时注入，不改变既有 seed-search/validation 默认行为。尚未执行 GPU 任务。 |
| 2026-09-02 | 单任务扫描入口 | 新增 `evaluate_robotwin_friction.py`：读取单任务归档、按 phase 取前三个 seed、复用一次模型加载依次执行七个摩擦值，并写逐试验 JSON、42 行 CSV、run config 和任务 summary。专家前检失败保留在固定分母中，不重试。尚未执行 GPU 任务。 |
| 2026-09-02 | 汇总与绘图入口 | 新增 `summarize_robotwin_friction.py`：从 50 个任务输出汇总原始记录、逐任务平均和逐摩擦总体成功率，生成 100 张逐任务图、1 张总体图及中文 `summary.md`。当前环境已有 matplotlib/pandas，无需修改依赖。尚未生成正式报告。 |
| 2026-09-02 | 正式作业清单 | 新增 `friction-jobs.json`，以统一 argv 模板描述 50 个任务；每项读取自己的 YAML、使用调度器分配的一张 GPU，并写入独立 `{output_dir}`。尚未 dry-run 或正式提交。 |
| 2026-09-02 | 静态检查与 dry-run | 四个相关 Python 文件通过 `py_compile`，两个新入口的 `--help` 和 `git diff --check` 通过；50 个作业与 50 份 YAML 完全一致，clean/random 共选取 300 个 seed 槽位。临时调度 dry-run 生成 50 个 queued 作业，确认 GPU `0–4`、每卡容量 2，未启动子进程。临时目录为 `/tmp/fastwam-friction-dry-run.wcQQgg/output/`。 |
| 2026-09-02 | 单条件 smoke test | 在 GPU 0 运行 `click_bell` clean、摩擦 `0.50`、环境 seed `4300000` 的一个试验；进程 exit code 0，专家与策略成功，逐试验 JSON、1 行 CSV 和 summary 均生成，static/dynamic friction 均记录为 `0.5`。结果位于 `evaluate_results/robotwin/friction_sweep/smoke_click_bell_f050_20260902/`。 |
| 2026-09-02 10:10 +08:00 | 正式批次提交 | 提交前未发现相关进程、queued/running SQLite 作业或 GPU `0–4` 占用。通过普通 `nohup + setsid` 启动 50 项一次性 SQLite 队列，GPU `0–4`、每卡最多 2 项、单项超时 10 小时；launcher PID 为 `3349468`。结果根目录为 `evaluate_results/robotwin/friction_sweep/all_tasks_7values_3seeds_20260902_101043/`。本行只表示已提交，不表示任务成功。 |
| 2026-09-02 10:10 +08:00 | 启动核验 | SQLite 为 10 项 `running`、40 项 `queued`，GPU `0–4` 各分配两个任务；launcher PID `3349468` 的 PPID 为 1，SID/PGID 均为自身。GPU 已出现对应显存占用，说明调度器脱离终端后正常派发。 |

## 运行项

正式批次有 10 项运行、40 项排队；由同一个 SQLite 调度器管理 GPU `0–4`。

## 失败项与资源问题

当前没有失败项或资源问题。

## 关键决策

- 仅扫描 RoboTwin 声明的 `scene.default_physical_material`，保证 `0.50` 与当前代码基线一致；不把结论表述为全场景统一摩擦。
- 专家前检失败按固定分母计为失败，不自动替换 seed 或重试。
- 每个任务作为一个调度作业，在单张 GPU 上复用一次模型加载完成 42 个实验单元。
- 不创建 Git commit；除非用户另行明确要求。

## 产物位置

- 任务书：[plan.md](plan.md)
- 账本：本文件
- successful seeds 来源：`../2026-08-27-robotwin-all-tasks-seed-search/successful-seeds/`
- 正式作业清单：`friction-jobs.json`
- 正式结果根目录：`evaluate_results/robotwin/friction_sweep/all_tasks_7values_3seeds_20260902_101043/`
- 正式 launcher 日志/PID：上述根目录同名前缀的 `.launcher.log` 与 `.launcher.pid`

## 下一步

1. 实现最小摩擦参数透传、单任务扫描和汇总脚本。
2. 完成最小静态检查、单条件 smoke test 和 50 作业 dry-run。
3. 确认 GPU 与队列仍空闲后提交正式批次。
