# FastWAM / RoboTwin GPU 环境

本文档说明如何在本仓库建立可复现的 FastWAM + RoboTwin 评测环境。环境使用 **uv**、CUDA 12.8 PyTorch 和仓库内的 **CuRobo GPU 规划器**；运动规划不使用复制版中的 MPlib 回退补丁。

运行根目录固定为 `third_party/RoboTwin`。完成配置后，代码、任务配置、CuRobo 源码、assets 与 checkpoint 都从当前工作目录读取，不依赖 `/data/fastwam`。

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

`pyproject.toml` 已设置两个下载源：普通 Python 包默认使用清华 PyPI 镜像；`torch` 和 `torchvision` 的 CUDA 12.8 轮子固定从 PyTorch 官方索引获取。无需再设置 pip 镜像环境变量。

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

在仓库根目录执行：

```bash
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_CUDA_ARCH_LIST=9.0  # H100；其他 GPU 请修改

uv sync --extra robotwin --python 3.10
```

该命令创建 `.venv`、按 `uv.lock` 安装 FastWAM 与 RoboTwin 依赖。`uv.lock` 是本项目环境的一部分，应随代码提交；`.venv` 不应提交。

### PyTorch 官方源较慢时

可将下列 wheel 临时放在仓库的上一级目录（`../`，不属于本仓库）：

```text
torch-2.7.1+cu128-cp310-cp310-manylinux_2_28_x86_64.whl
torchvision-0.22.1+cu128-cp310-cp310-manylinux_2_28_x86_64.whl
```

官方 URL 和 SHA-256：

```text
https://download-r2.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp310-cp310-manylinux_2_28_x86_64.whl
d6c3cba198dc93f93422a8545f48a6697890366e4b9701f54351fc27e2304bd3

https://download-r2.pytorch.org/whl/cu128/torchvision-0.22.1%2Bcu128-cp310-cp310-manylinux_2_28_x86_64.whl
538f4db667286d939b4eee0a66d31ed21b51186668006b0e0ffe20338ecc7e00
```

先创建环境并安装本地 wheel，再由 uv 安装其余依赖：

```bash
uv venv --python 3.10
uv pip install --python .venv/bin/python --no-deps \
  ../torch-2.7.1+cu128-cp310-cp310-manylinux_2_28_x86_64.whl \
  ../torchvision-0.22.1+cu128-cp310-cp310-manylinux_2_28_x86_64.whl

uv sync --extra robotwin --frozen --inexact \
  --no-install-package torch \
  --no-install-package torchvision \
  --python .venv/bin/python
```

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

仅本地：  third_party/RoboTwin/assets/、checkpoints/、.venv/、CuRobo *.so
```

评测默认使用 `configs/sim_robotwin.yaml`：RoboTwin 根目录为 `third_party/RoboTwin`，默认任务配置为 `demo_randomized`。RoboTwin 会从 `third_party/RoboTwin/task_config/` 读取 `demo_randomized.yml` 以及相机、embodiment、步数限制等配套 YAML。

assets 和 checkpoint 必须已在本地就绪，才可运行 RoboTwin 评测；它们体积较大，故不进入 Git。评测入口示例与具体任务参数保留在项目原 README 和 Hydra 配置中，本文件不重复展开。

## 7. 提交前检查

本次配置不执行 `git add` 或 `git commit`。提交前确认大文件和本机编译产物没有被加入：

```bash
git status --short
git check-ignore -v third_party/RoboTwin/assets/objects
git check-ignore -v checkpoints/fastwam_release/robotwin_uncond_3cam_384.pt
git check-ignore -v third_party/RoboTwin/envs/curobo/src/curobo/curobolib/geom_cu.cpython-310-x86_64-linux-gnu.so
```
