# FastWAM / RoboTwin GPU 环境建立与使用指南

本文档说明如何在本仓库建立可复现的 FastWAM + RoboTwin 评测环境。环境使用 **uv**、CUDA 12.8 PyTorch 和仓库内的 **CuRobo GPU 规划器**。

运行根目录固定为 `third_party/RoboTwin`。代码、任务配置和 CuRobo 源码均从当前工作目录读取；依赖缓存与可共享的大资源统一存放在 `/data/shared/FastWAM`。RoboTwin 仍使用仓库内的相对资源路径，新的工作副本由本文第 3 节的一键脚本将共享副本复制到自身目录；复制完成后的评测不依赖原始资源目录或共享盘中的资源文件。

## 1. 已固定的版本与约束

| 组件 | 固定值 | 原因 |
| --- | --- | --- |
| Python | 3.10 | RoboTwin 与 CuRobo 的当前编译目标 |
| PyTorch | 2.7.1+cu128 | CUDA 12.8 轮子 |
| NumPy | 1.26.4 | 与已验证的复制版一致；`mplib==0.2.1` 要求 `numpy<2` |
| OpenCV | 4.10.0.84 | 与 NumPy 1.26 兼容 |
| setuptools | 79.0.1 | `sapien==3.0.0b1` 仍需要 `pkg_resources` |
| CuRobo | `third_party/RoboTwin/envs/curobo` | 在本机针对 GPU 架构编译 CUDA 扩展 |

虽然主运动规划器是 CuRobo，RoboTwin 仍通过 MPlib 执行 TOPP 时间参数化。因此 MPlib 是运行依赖，但不承担 CuRobo 的回退规划功能。

## 2. 系统前提

一键脚本面向 Linux x86_64、CPython 3.10、CUDA Toolkit 12.8 和 H100（compute capability 9.0）主机。Python 开发头文件是 CuRobo 编译的必需项；多 H100 / NVSwitch 主机还需要与驱动版本一致且已完成初始化的 NVIDIA Fabric Manager。

脚本会检查这些系统条件，但不使用 `apt`、`sudo` 或替换系统 Python/CUDA。完整的检查顺序、手动命令和原理说明保留在 `scripts/setup_vcl_env.sh` 的对应注释中。

## 3. 一键配置环境

推荐在仓库根目录一键执行：

```bash
bash scripts/setup_vcl_env.sh
```

脚本先严格检查 Linux x86_64、CPython 3.10 和开发头文件、CUDA Toolkit 12.8、可用的 H100（compute capability 9.0）、NVSwitch Fabric 状态、共享缓存、锁文件和共享资源。任一系统依赖缺失或不匹配都会直接报错；脚本不会使用 `apt`、`sudo` 或替换 CUDA/Python。仅当 `uv` 缺失时，才通过官方安装器安装最新版；已有 `uv` 不限制版本。之后脚本会离线同步依赖、编译 CuRobo，并将缺失的 assets 和 checkpoints 复制为本地实体目录。已有资源会以校验和 dry-run 与共享副本比对，不一致时直接报错，不会覆盖或合并。

只检查而不写入时执行：

```bash
bash scripts/setup_vcl_env.sh --check
```

`--check` 会读取并校验大资源，因此需要一些时间，但不会安装、编译或复制任何内容。手动同步 uv 环境、编译 CuRobo、复制资源和验证 CUDA 扩展的等价命令及原理说明，已按执行顺序移到 `scripts/setup_vcl_env.sh` 的注释中。

## 4. RoboTwin 运行资源与配置

版本管理与本地大文件的边界如下：

```text
纳入 Git：third_party/RoboTwin/task_config/、third_party/RoboTwin/envs/curobo/、
          pyproject.toml、uv.lock、README_VCL.md

仅本地：  third_party/RoboTwin/assets/、third_party/RoboTwin/checkpoints/、
          checkpoints/、.venv/、CuRobo *.so

共享副本：/data/shared/FastWAM/third_party/RoboTwin/assets/、
          /data/shared/FastWAM/third_party/RoboTwin/checkpoints/、
          /data/shared/FastWAM/checkpoints/、
          /data/shared/FastWAM/uv-cache/
```

评测默认使用 `configs/sim_robotwin.yaml`：RoboTwin 根目录为 `third_party/RoboTwin`，默认任务配置为 `demo_randomized`。RoboTwin 会从 `third_party/RoboTwin/task_config/` 读取 `demo_randomized.yml` 以及相机、embodiment、步数限制等配套 YAML。

assets 和 checkpoint 必须已在本地就绪，才可运行 RoboTwin 评测；它们体积较大，故不进入 Git。共享盘中的副本只作为分发源。`scripts/setup_vcl_env.sh` 会把缺失资源复制为本地实体目录；已存在的目录必须与共享副本一致，脚本不会覆盖或合并差异内容。复制完成后，评测不再依赖共享盘中的资源文件。

评测入口示例与具体任务参数保留在项目原 README 和 Hydra 配置中，本文件不重复展开。

## 5. 实验文档快速目录

下列字符树只索引已稳定的总结与可复用归档，不在此复制实验结论。新增稳定实验后，按相同格式继续追加即可。

```text
docs/experiments/
|----- 2026-08-27-robotwin-all-tasks-seed-search/
|      |----- summary.md
|      \----- successful-seeds/
|             \----- <task>.yaml    # 50 个任务的 successful seeds 归档
\----- 2026-08-29-robotwin-all-tasks-seed-validation/
       \----- summary.md
```

- `2026-08-27` 的 `summary.md` 总结全任务 seed 搜索，`successful-seeds/` 保存对应 YAML 配置。
- `2026-08-29` 的 `summary.md` 汇总全部 successful seeds 的独立验证结果。

## 6. 全局 GPU 任务调度器

仓库通过 `experiments/robotwin/schedule_robotwin_seed_search.py` 为跨任务实验提供统一的 SQLite GPU FIFO 队列。文件名保留了最初的 seed-search 用途，但当前 `--jobs-file` 接口可调度任意以 `uv run` 启动的命令作业，不与搜索或验证逻辑绑定。

- 作业 JSON 可在 argv 中使用 `{gpu_id}`、`{job_name}` 和 `{output_dir}`，让同一模板安全展开为多个独立任务；`--dry-run` 可只建立队列和渲染配置，不启动子进程。
- 调度器按 FIFO 消费队列，通过 `--gpu-ids` 和 `--max-tasks-per-gpu` 控制每张 GPU 的并发容量，槽位释放后自动启动后续作业。
- 每个作业拥有独立的输出目录和 launcher 日志；队列状态、GPU 分配、启停时间、退出码和事件持久化到 SQLite，避免多个任务并发写同一份结果或日志。
- 作业超时、失败或收到终止信号时，调度器按独立进程组收尾并记录终态；队列消费完毕后正常退出，不需要 systemd 或常驻 service。

当前调度器是一次性批次 consumer，不提供运行中追加、常驻模式或跨调度器 GPU 锁。如需并行启动多个批次，应为它们显式划分不重叠的 GPU 集合。已运行的作业配置示例保存在 `docs/experiments/2026-08-29-robotwin-all-tasks-seed-validation/` 下的 `*-jobs.json` 文件中。
