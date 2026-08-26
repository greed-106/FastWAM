#!/usr/bin/env bash
set -euo pipefail

readonly REQUIRED_PYTHON_VERSION="3.10"
readonly REQUIRED_CUDA_VERSION="12.8"
readonly REQUIRED_COMPUTE_CAPABILITY="9.0"
readonly REQUIRED_TORCH_VERSION="2.7.1+cu128"
readonly REQUIRED_LOCK_SHA256="17c713ac44705d21ec0b688bdce651e968cfeefac87d4d0c81f9e56adcccbe20"
readonly SHARED_ROOT="/data/shared/FastWAM"
readonly CACHE_DIR="${SHARED_ROOT}/uv-cache"
readonly PYTHON_BIN="/usr/bin/python3.10"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[setup] %s\n' "$*"
}

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_vcl_env.sh [--check]

Without arguments, validate the host, install the latest uv only when it is
missing, create the offline environment, compile CuRobo, and copy missing
RoboTwin assets/checkpoints as local physical directories.

--check  Validate all prerequisites and existing local resources without
         installing uv, creating a virtual environment, compiling, or copying.
EOF
}

check_only=0
if (( $# > 1 )); then
  usage >&2
  exit 2
fi
case "${1:-}" in
  "") ;;
  --check) check_only=1 ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/.." && pwd -P)"
cd -- "${repo_root}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "缺少命令 '$1'；脚本不会自动安装系统依赖。"
}

require_dir() {
  [[ -d "$1" ]] || die "$2 不存在或不是目录：$1"
}

require_physical_dir() {
  [[ -d "$1" && ! -L "$1" ]] || die "$2 必须是实体目录而非软链接：$1"
}

require_file() {
  [[ -f "$1" ]] || die "$2 不存在或不是普通文件：$1"
}

require_readable_dir() {
  require_dir "$1" "$2"
  [[ -r "$1" && -x "$1" ]] || die "$2 不可读或不可遍历：$1"
}

ensure_no_symlinks() {
  local path="$1"
  local label="$2"
  local first_link

  first_link="$(find "$path" -type l -print -quit)"
  [[ -z "$first_link" ]] || die "${label} 包含软链接，拒绝复用：${first_link}"
}

verify_resource_layout() {
  local root="$1"
  local label="$2"
  local assets="${root}/third_party/RoboTwin/assets"
  local robotwin_checkpoints="${root}/third_party/RoboTwin/checkpoints"
  local fastwam_checkpoints="${root}/checkpoints/fastwam_release"

  require_physical_dir "$assets" "${label} assets"
  require_physical_dir "$robotwin_checkpoints" "${label} RoboTwin checkpoints"
  require_physical_dir "$fastwam_checkpoints" "${label} FastWAM checkpoints"
  ensure_no_symlinks "$assets" "${label} assets"
  ensure_no_symlinks "$robotwin_checkpoints" "${label} RoboTwin checkpoints"
  ensure_no_symlinks "$fastwam_checkpoints" "${label} FastWAM checkpoints"

  require_dir "${assets}/background_texture" "${label} assets/background_texture"
  require_dir "${assets}/embodiments" "${label} assets/embodiments"
  require_dir "${assets}/objects" "${label} assets/objects"
  require_file "${robotwin_checkpoints}/DiffSynth-Studio/Wan-Series-Converted-Safetensors/models_t5_umt5-xxl-enc-bf16.safetensors" "${label} T5 checkpoint"
  require_file "${robotwin_checkpoints}/DiffSynth-Studio/Wan-Series-Converted-Safetensors/Wan2.2_VAE.safetensors" "${label} VAE checkpoint"
  require_file "${robotwin_checkpoints}/Wan-AI/Wan2.1-T2V-1.3B/google/umt5-xxl/tokenizer.json" "${label} tokenizer"
  require_file "${fastwam_checkpoints}/robotwin_uncond_3cam_384.pt" "${label} policy checkpoint"
  require_file "${fastwam_checkpoints}/robotwin_uncond_3cam_384_dataset_stats.json" "${label} policy statistics"
}

compare_resource_tree() {
  local source="$1"
  local destination="$2"
  local label="$3"
  local exclude_temp="$4"
  local diff
  local -a rsync_args=(
    -aHnc
    --delete
    --quiet
    --no-owner
    --no-group
    --out-format='%i %n%L'
  )

  if [[ "$exclude_temp" == "true" ]]; then
    rsync_args+=(--exclude='._____temp/')
  fi

  if ! diff="$(rsync "${rsync_args[@]}" "${source}/" "${destination}/")"; then
    die "无法校验 ${label}：rsync dry-run 失败。"
  fi
  if [[ -n "$diff" ]]; then
    printf '%s\n' "$diff" | sed -n '1,20p' >&2
    die "${label} 与共享副本不一致；脚本不会覆盖或合并已有目录。"
  fi
}

declare -a missing_sources=()
declare -a missing_destinations=()
declare -a missing_labels=()
declare -a missing_exclude_temp=()

plan_resource() {
  local source="$1"
  local destination="$2"
  local label="$3"
  local exclude_temp="$4"

  if [[ -e "$destination" || -L "$destination" ]]; then
    require_physical_dir "$destination" "本地 ${label}"
    ensure_no_symlinks "$destination" "本地 ${label}"
    compare_resource_tree "$source" "$destination" "$label" "$exclude_temp"
    return
  fi

  missing_sources+=("$source")
  missing_destinations+=("$destination")
  missing_labels+=("$label")
  missing_exclude_temp+=("$exclude_temp")
}

check_disk_space_for_missing_resources() {
  local required_kib=0
  local source_kib
  local available_kib
  local reserve_kib
  local index

  if (( ${#missing_sources[@]} == 0 )); then
    return 0
  fi

  for index in "${!missing_sources[@]}"; do
    source_kib="$(du -sk "${missing_sources[$index]}" | awk '{print $1}')"
    [[ "$source_kib" =~ ^[0-9]+$ ]] || die "无法统计 ${missing_labels[$index]} 的磁盘占用。"
    required_kib=$((required_kib + source_kib))
  done

  available_kib="$(df -Pk "$repo_root" | awk 'END {print $4}')"
  [[ "$available_kib" =~ ^[0-9]+$ ]] || die "无法读取目标工作树的可用磁盘空间。"
  reserve_kib=$((required_kib / 20 + 1024 * 1024))
  if (( available_kib < required_kib + reserve_kib )); then
    die "磁盘空间不足以复制缺失资源：需要至少 $(( (required_kib + reserve_kib) / 1024 / 1024 )) GiB 可用空间（含 5% 和 1 GiB 余量）。"
  fi
}

copy_missing_resources() {
  local index
  local source
  local destination
  local label
  local parent
  local staging

  for index in "${!missing_sources[@]}"; do
    source="${missing_sources[$index]}"
    destination="${missing_destinations[$index]}"
    label="${missing_labels[$index]}"
    parent="$(dirname -- "$destination")"

    mkdir -p -- "$parent"
    [[ -w "$parent" && -x "$parent" ]] || die "本地 ${label} 的父目录不可写：${parent}"
    staging="$(mktemp -d "${parent}/.fastwam-resource.partial.XXXXXX")" || die "无法为 ${label} 创建临时复制目录。"

    info "正在复制 ${label} 到本地实体目录（可保留临时目录以便故障排查）：${destination}"
    if ! cp -a --no-preserve=ownership -- "${source}/." "${staging}/"; then
      die "复制 ${label} 失败；部分数据保留在 ${staging}，脚本未修改目标目录。"
    fi
    if [[ -e "$destination" || -L "$destination" ]]; then
      die "复制 ${label} 期间目标目录出现：${destination}；临时数据保留在 ${staging}。"
    fi
    if ! mv -T -- "$staging" "$destination"; then
      die "无法原子完成 ${label} 的复制；临时数据保留在 ${staging}。"
    fi
  done
}

UV_BIN=""
UV_VERSION=""
ensure_uv() {
  local uv_install_dir="${UV_INSTALL_DIR:-${HOME}/.local/bin}"
  local candidate=""
  local installed_version

  if [[ -x "${uv_install_dir}/uv" ]]; then
    candidate="${uv_install_dir}/uv"
  elif command -v uv >/dev/null 2>&1; then
    candidate="$(command -v uv)"
  fi

  if [[ -z "$candidate" ]]; then
    (( check_only == 0 )) || die "未找到 uv；--check 不会安装它。"
    require_command curl
    mkdir -p -- "$uv_install_dir"
    [[ -w "$uv_install_dir" && -x "$uv_install_dir" ]] || die "uv 安装目录不可写：${uv_install_dir}"
    info "未找到 uv，正在安装最新版到 ${uv_install_dir}"
    if ! curl --fail --silent --show-error --location "https://astral.sh/uv/install.sh" \
      | env -u UV_INSTALL_DIR UV_UNMANAGED_INSTALL="$uv_install_dir" UV_NO_MODIFY_PATH=1 sh; then
      die "uv 安装失败；不会安装任何其他依赖。"
    fi
    candidate="${uv_install_dir}/uv"
  fi

  [[ -x "$candidate" ]] || die "uv 安装后不可执行：${candidate}"
  installed_version="$("$candidate" --version | awk '{print $2}')"
  [[ -n "$installed_version" ]] || die "无法读取 uv 版本：${candidate}"
  UV_BIN="$candidate"
  UV_VERSION="$installed_version"
}

require_command sha256sum
require_command awk
require_command cp
require_command df
require_command du
require_command g++
require_command git
require_command make
require_command mv
require_command nvidia-smi
require_command rsync

[[ "$(uname -s)" == "Linux" ]] || die "仅支持 Linux。"
case "$(uname -m)" in
  x86_64|amd64) ;;
  *) die "仅支持 Linux x86_64；当前架构为 $(uname -m)。" ;;
esac

require_file "${repo_root}/pyproject.toml" "项目 pyproject.toml"
require_file "${repo_root}/uv.lock" "项目 uv.lock"
require_file "${repo_root}/third_party/RoboTwin/envs/curobo/setup.py" "CuRobo setup.py"

[[ -x "$PYTHON_BIN" ]] || die "需要 ${PYTHON_BIN}；脚本不会安装 Python。"
python_version="$("$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
python_implementation="$("$PYTHON_BIN" -c 'import platform; print(platform.python_implementation())')"
python_include="$("$PYTHON_BIN" -c 'import sysconfig; print(sysconfig.get_path("include"))')"
[[ "$python_version" == "$REQUIRED_PYTHON_VERSION" ]] || die "Python 版本为 ${python_version}，要求 ${REQUIRED_PYTHON_VERSION}。"
[[ "$python_implementation" == "CPython" ]] || die "Python 实现为 ${python_implementation}，要求 CPython。"
[[ -f "${python_include}/Python.h" ]] || die "缺少 Python 开发头文件：${python_include}/Python.h"

cuda_home="${CUDA_HOME:-/usr/local/cuda}"
require_dir "$cuda_home" "CUDA_HOME"
nvcc_bin="${cuda_home}/bin/nvcc"
[[ -x "$nvcc_bin" ]] || die "缺少可执行的 nvcc：${nvcc_bin}"
nvcc_output="$("$nvcc_bin" --version)"
if [[ "$nvcc_output" =~ release[[:space:]]+([0-9]+\.[0-9]+) ]]; then
  cuda_version="${BASH_REMATCH[1]}"
else
  die "无法从 nvcc 输出识别 CUDA 版本。"
fi
[[ "$cuda_version" == "$REQUIRED_CUDA_VERSION" ]] || die "CUDA Toolkit 为 ${cuda_version}，要求 ${REQUIRED_CUDA_VERSION}。"
export CUDA_HOME="$cuda_home"
export PATH="${CUDA_HOME}/bin:${PATH}"

gpu_capabilities="$(LC_ALL=C nvidia-smi --query-gpu=compute_cap --format=csv,noheader,nounits)" || die "nvidia-smi 无法访问 GPU。"
mapfile -t gpu_capability_lines <<< "$gpu_capabilities"
(( ${#gpu_capability_lines[@]} > 0 )) || die "未检测到 GPU。"
for gpu_capability in "${gpu_capability_lines[@]}"; do
  gpu_capability="${gpu_capability//[[:space:]]/}"
  [[ "$gpu_capability" == "$REQUIRED_COMPUTE_CAPABILITY" ]] || die "GPU compute capability 为 ${gpu_capability}，要求 ${REQUIRED_COMPUTE_CAPABILITY}（H100 配置）。"
done
export TORCH_CUDA_ARCH_LIST="$REQUIRED_COMPUTE_CAPABILITY"

gpu_count="${#gpu_capability_lines[@]}"
gpu_details="$(LC_ALL=C nvidia-smi -q)" || die "无法读取 GPU 详细状态。"
fabric_state_lines="$(grep -Ec '^[[:space:]]*State[[:space:]]*:' <<< "$gpu_details" || true)"
fabric_na_lines="$(grep -Ec '^[[:space:]]*State[[:space:]]*:[[:space:]]*N/A[[:space:]]*$' <<< "$gpu_details" || true)"
if (( fabric_state_lines > fabric_na_lines )); then
  require_command systemctl
  [[ "$(systemctl is-active nvidia-fabricmanager 2>/dev/null || true)" == "active" ]] || die "检测到 Fabric 状态，但 nvidia-fabricmanager 未处于 active。"
  fabric_completed="$(grep -Ec '^[[:space:]]*State[[:space:]]*:[[:space:]]*Completed[[:space:]]*$' <<< "$gpu_details" || true)"
  fabric_success="$(grep -Ec '^[[:space:]]*Status[[:space:]]*:[[:space:]]*Success[[:space:]]*$' <<< "$gpu_details" || true)"
  (( fabric_completed == gpu_count && fabric_success == gpu_count )) || die "NVIDIA Fabric 未对全部 ${gpu_count} 张 GPU 完成初始化。"
fi

require_readable_dir "$SHARED_ROOT" "共享 FastWAM 根目录"
require_physical_dir "$CACHE_DIR" "共享 uv 缓存"
require_file "${CACHE_DIR}/README.md" "共享 uv 缓存说明"
lock_sha256="$(sha256sum "${repo_root}/uv.lock" | awk '{print $1}')"
[[ "$lock_sha256" == "$REQUIRED_LOCK_SHA256" ]] || die "当前 uv.lock SHA256 为 ${lock_sha256}，不匹配共享缓存合同。"
grep -Fq "$lock_sha256" "${CACHE_DIR}/README.md" || die "共享缓存说明未声明当前 uv.lock SHA256；拒绝继续。"
export UV_CACHE_DIR="$CACHE_DIR"
export UV_LINK_MODE="copy"

verify_resource_layout "$SHARED_ROOT" "共享资源"
plan_resource "${SHARED_ROOT}/third_party/RoboTwin/assets" "${repo_root}/third_party/RoboTwin/assets" "RoboTwin assets" "false"
plan_resource "${SHARED_ROOT}/third_party/RoboTwin/checkpoints" "${repo_root}/third_party/RoboTwin/checkpoints" "RoboTwin checkpoints" "true"
plan_resource "${SHARED_ROOT}/checkpoints" "${repo_root}/checkpoints" "FastWAM checkpoints" "false"
if (( check_only == 0 )); then
  check_disk_space_for_missing_resources
fi
ensure_uv

if (( check_only )); then
  (( ${#missing_sources[@]} == 0 )) || die "本地资源目录缺失；请去掉 --check 重新执行，以复制实体副本。"
  verify_resource_layout "$repo_root" "本地资源"
  info "预检通过：${gpu_count} 张 GPU、CUDA ${cuda_version}、Python ${python_version}、uv ${UV_VERSION}、共享缓存和本地实体资源均匹配。"
  exit 0
fi

info "使用共享缓存离线创建 Python 环境"
"$UV_BIN" sync --extra robotwin --locked --offline --no-python-downloads --python "$PYTHON_BIN"

info "编译仓库内的 CuRobo GPU 扩展"
"$UV_BIN" pip install --python "${repo_root}/.venv/bin/python" --no-build-isolation --no-deps -e "${repo_root}/third_party/RoboTwin/envs/curobo"

copy_missing_resources
verify_resource_layout "$repo_root" "本地资源"
for resource_index in "${!missing_sources[@]}"; do
  compare_resource_tree "${missing_sources[$resource_index]}" "${missing_destinations[$resource_index]}" "${missing_labels[$resource_index]}" "${missing_exclude_temp[$resource_index]}"
done

info "验证 Python、PyTorch CUDA 与 CuRobo"
"$UV_BIN" pip check --python "${repo_root}/.venv/bin/python"
FASTWAM_EXPECTED_TORCH_VERSION="$REQUIRED_TORCH_VERSION" \
FASTWAM_EXPECTED_CUDA_VERSION="$REQUIRED_CUDA_VERSION" \
FASTWAM_EXPECTED_COMPUTE_CAPABILITY="$REQUIRED_COMPUTE_CAPABILITY" \
CUDA_VISIBLE_DEVICES=0 \
"${repo_root}/.venv/bin/python" - <<'PY'
import os

import torch

if torch.__version__ != os.environ["FASTWAM_EXPECTED_TORCH_VERSION"]:
    raise SystemExit(
        f"torch={torch.__version__}, expected={os.environ['FASTWAM_EXPECTED_TORCH_VERSION']}"
    )
if torch.version.cuda != os.environ["FASTWAM_EXPECTED_CUDA_VERSION"]:
    raise SystemExit(
        f"torch CUDA={torch.version.cuda}, expected={os.environ['FASTWAM_EXPECTED_CUDA_VERSION']}"
    )
if not torch.cuda.is_available():
    raise SystemExit("PyTorch cannot access CUDA")

expected_capability = os.environ["FASTWAM_EXPECTED_COMPUTE_CAPABILITY"]
actual_capability = ".".join(map(str, torch.cuda.get_device_capability(0)))
if actual_capability != expected_capability:
    raise SystemExit(f"GPU compute capability={actual_capability}, expected={expected_capability}")

# Load torch first so CuRobo extensions can resolve libtorch/libc10.
from curobo.curobolib import geom_cu, kinematics_fused_cu

print(f"PyTorch {torch.__version__}, CUDA {torch.version.cuda}, GPU {torch.cuda.get_device_name(0)}")
print(geom_cu.__name__, kinematics_fused_cu.__name__)
PY

info "配置完成：环境、CuRobo 和本地实体资源均已就绪。"
