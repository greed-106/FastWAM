# FastWAM / RoboTwin GPU 环境

本文档说明如何在本仓库建立可复现的 FastWAM + RoboTwin 评测环境。环境使用 **uv**、CUDA 12.8 PyTorch 和仓库内的 **CuRobo GPU 规划器**；运动规划不使用复制版中的 MPlib 回退补丁。

运行根目录固定为 `third_party/RoboTwin`。代码、任务配置和 CuRobo 源码均从当前工作目录读取；依赖缓存与可共享的大资源统一存放在 `/data/shared/FastWAM`。RoboTwin 仍使用仓库内的相对资源路径，新的工作副本应按本文第 6 节将共享副本复制到自身目录；复制完成后的评测不依赖原始资源目录或共享盘中的资源文件。

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

以下命令以 Ubuntu/Debian、H100 为例。其他 GPU 应将 `TORCH_CUDA_ARCH_LIST` 改为对应 compute capability。

```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-dev

uv --version
/usr/local/cuda/bin/nvcc --version
nvidia-smi
test -f /usr/include/python3.10/Python.h && echo "Python 开发头文件已就绪"
```

`python3.10-dev` 不是可选项：CuRobo 编译 C++/CUDA 扩展时需要 `Python.h`。

### 多 H100 / NVSwitch 主机

多 GPU NVSwitch 主机还需要与驱动**完全同版本**的 NVIDIA Fabric Manager。否则 PyTorch 常在 `cudaGetDeviceCount()` 报 `Error 802: system not yet initialized`。

```bash
systemctl is-active nvidia-fabricmanager
nvidia-smi -q | grep -A2 'Fabric'
```

服务应为 `active`，每张卡的 `Fabric State` 应为 `Completed`、`Status` 应为 `Success`。例如驱动为 `610.43.02` 时，Fabric Manager 也必须为 `610.43.02`；不可混用其他主版本。首次安装后通常需要重启主机，让驱动、NVSwitch 和 Fabric Manager 按正确顺序初始化。

## 3. 用 uv 创建环境

推荐在仓库根目录一键执行：

```bash
bash scripts/setup_vcl_env.sh
```

脚本先严格检查 Linux x86_64、CPython 3.10 和开发头文件、CUDA Toolkit 12.8、可用的 H100（compute capability 9.0）、NVSwitch Fabric 状态、共享缓存、锁文件和共享资源。任一系统依赖缺失或不匹配都会直接报错；脚本不会使用 `apt`、`sudo` 或替换 CUDA/Python。仅当 `uv` 缺失时，才通过官方安装器安装最新版；已有 `uv` 不限制版本。之后脚本会离线同步依赖、编译 CuRobo，并将缺失的 assets 和 checkpoints 复制为本地实体目录。已有资源会以校验和 dry-run 与共享副本比对，不一致时直接报错，不会覆盖或合并。

只检查而不写入时执行：

```bash
bash scripts/setup_vcl_env.sh --check
```

`--check` 会读取并校验大资源，因此需要一些时间，但不会安装、编译或复制任何内容。

如需手动执行其中的 Python 依赖同步，可在仓库根目录运行：

```bash
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=9.0  # H100；其他 GPU 请修改
export UV_CACHE_DIR=/data/shared/FastWAM/uv-cache
export UV_LINK_MODE=copy  # .venv 与共享缓存之间不创建硬链接

uv sync --extra robotwin --locked --offline --no-python-downloads --python 3.10
```

该命令创建 `.venv`、按 `uv.lock` 从共享缓存安装 FastWAM 与 RoboTwin 依赖，且 `--offline` 禁止回退到网络。`UV_LINK_MODE=copy` 使环境文件成为独立副本，避免对 `.venv` 的修改影响共享缓存。`uv.lock` 是本项目环境的一部分，应随代码提交；`.venv` 不应提交。共享缓存已按 Linux x86_64、CPython 3.10、CUDA 12.8 的当前锁文件准备；若锁文件或平台改变，uv 会明确报出缺失项，应由共享缓存维护者先在线补齐对应缓存，目标工作副本仍保持 `--offline`。

## 4. 编译仓库内的 CuRobo

CuRobo 源码已位于 `third_party/RoboTwin/envs/curobo`，不需要再次 `git clone`。使用当前 uv 环境的 PyTorch 和 CUDA 工具链编译：

```bash
CUDA_HOME=/usr/local/cuda \
TORCH_CUDA_ARCH_LIST=9.0 \
uv pip install --python .venv/bin/python \
  --no-build-isolation --no-deps \
  -e third_party/RoboTwin/envs/curobo
```

`--no-build-isolation` 使 `CUDAExtension` 使用 `.venv` 中的 PyTorch 头文件和库。构建产物为 `src/curobo/curobolib/*.so`，它们与机器、驱动、CUDA 和 PyTorch 版本绑定，已被 Git 忽略；更换其中任一项后重新执行本节命令。

## 5. 验证

在 Fabric 已完成初始化后执行：

```bash
CUDA_VISIBLE_DEVICES=0 uv run --no-sync python - <<'PY'
import torch

# 必须先加载 torch，使 CuRobo 扩展能找到 libc10/libtorch。
from curobo.curobolib import geom_cu, kinematics_fused_cu

print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_device_name(0))
x = torch.tensor([1.0, 2.0, 3.0], device="cuda")
print((x * x).sum().item())
print(geom_cu.__name__, kinematics_fused_cu.__name__)
PY

uv pip check --python .venv/bin/python
```

预期会打印 CUDA 12.8、GPU 名称、`14.0`，并显示两个 CuRobo 扩展模块名。`uv pip check` 应报告所有已安装包兼容。

## 6. RoboTwin 运行资源与配置

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

assets 和 checkpoint 必须已在本地就绪，才可运行 RoboTwin 评测；它们体积较大，故不进入 Git。共享盘中的副本只作为分发源；当前工作树保留原有本地目录，不会被本步骤替换。`scripts/setup_vcl_env.sh` 会复制缺失资源为实体目录；若目标已存在，则先做校验和 dry-run，一旦不一致便报错，不会覆盖或合并。每个新工作副本因此独立，修改本地副本不会影响共享副本或其他用户。

在新的工作副本中，确认目标路径尚不存在后，复制资源目录：

```bash
test ! -e third_party/RoboTwin/assets
test ! -e third_party/RoboTwin/checkpoints
test ! -e checkpoints

cp -a --no-preserve=ownership /data/shared/FastWAM/third_party/RoboTwin/assets third_party/RoboTwin/
cp -a --no-preserve=ownership /data/shared/FastWAM/third_party/RoboTwin/checkpoints third_party/RoboTwin/
cp -a --no-preserve=ownership /data/shared/FastWAM/checkpoints .
```

上述命令会在工作副本中生成实体目录，而不是软链接；复制完成后可以不挂载共享盘运行评测。

评测入口示例与具体任务参数保留在项目原 README 和 Hydra 配置中，本文件不重复展开。

## 7. 提交前检查

本次配置不执行 `git add` 或 `git commit`。提交前确认大文件和本机编译产物没有被加入：

```bash
git status --short
git check-ignore -v third_party/RoboTwin/assets/objects
git check-ignore -v checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt
git check-ignore -v third_party/RoboTwin/envs/curobo/src/curobo/curobolib/geom_cu.cpython-310-x86_64-linux-gnu.so
```
