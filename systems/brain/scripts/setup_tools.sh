#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# setup_tools.sh — Install local chip simulators and testbench Python tools
#
# Purpose:
#   Downloads the prebuilt YosysHQ OSS CAD Suite (Verilator digital simulator,
#   Yosys hardware compiler, nextpnr-himbaechel Gowin FPGA placer/router, and
#   Icarus Verilog) plus a Python virtual environment (pytest, cocotb, pyyaml)
#   into `<repo>/.tools/` (gitignored) without modifying system directories.
#
# Usage:
#   bash systems/brain/scripts/setup_tools.sh
#
# Optional Environment Variables:
#   OSS_CAD_TAG   Override the pinned YosysHQ release tag (YYYY-MM-DD), e.g.:
#                   OSS_CAD_TAG=2026-11-12 bash systems/brain/scripts/setup_tools.sh
#                 Normally callers omit this and use PINNED_TAG below.
#
# Outputs:
#   <repo>/.tools/oss-cad-suite/  Extracted simulator and FPGA binaries
#   <repo>/.tools/.venv/          uv-managed Python testbench environment
#   <repo>/.tools/env.sh          Shell script to prepend both to PATH
# ==============================================================================

# Directory containing this script (`systems/brain/scripts/`).
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "${SCRIPTS_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BRAIN_DIR}/../.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/.tools"
OSS_CAD_DIR="${TOOLS_DIR}/oss-cad-suite"
VENV_DIR="${TOOLS_DIR}/.venv"
ENV_FILE="${TOOLS_DIR}/env.sh"

# Pinned upstream release for reproducible simulation and FPGA timing results.
# Bump policy: only update deliberately between phases when a new device fix or
# compiler bugfix is needed; afterwards remove `.tools/oss-cad-suite`, re-run
# this script, and re-verify the full testbench and synthesis suite.
PINNED_TAG="2026-11-12"

# Detect the host OS and CPU architecture and print the matching YosysHQ archive
# platform slug (e.g., `linux-x64`). Only Linux and macOS (Darwin) on x64/arm64
# are supported because YosysHQ only publishes `.tgz` archives for these four
# targets (Windows users should run inside WSL2 Linux).
detect_platform() {
  local uname_s uname_m os_part arch_part
  uname_s="$(uname -s)"
  uname_m="$(uname -m)"

  case "${uname_s}" in
    Linux)  os_part="linux" ;;
    Darwin) os_part="darwin" ;;
    *)
      echo "ERROR: Unsupported OS '${uname_s}'. Expected Linux (including WSL2) or macOS (Darwin)." >&2
      exit 1
      ;;
  esac

  case "${uname_m}" in
    x86_64|amd64)   arch_part="x64" ;;
    aarch64|arm64)  arch_part="arm64" ;;
    *)
      echo "ERROR: Unsupported CPU architecture '${uname_m}'. Expected x86_64 or arm64." >&2
      exit 1
      ;;
  esac

  echo "${os_part}-${arch_part}"
}

# Download and extract the prebuilt OSS CAD Suite tarball into `.tools/` if the
# required simulator/FPGA binaries are not already present. Safe to re-run.
install_oss_cad_suite() {
  local platform tag stamp asset_name url archive_path
  platform="$(detect_platform)"

  if [[ -x "${OSS_CAD_DIR}/bin/verilator" && -x "${OSS_CAD_DIR}/bin/yosys" && -x "${OSS_CAD_DIR}/bin/nextpnr-himbaechel" ]]; then
    echo "[setup_tools] oss-cad-suite already installed at ${OSS_CAD_DIR}"
    return 0
  fi

  tag="${OSS_CAD_TAG:-${PINNED_TAG}}"
  stamp="${tag//-/}"
  asset_name="oss-cad-suite-${platform}-${stamp}.tgz"
  url="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${tag}/${asset_name}"
  archive_path="${TOOLS_DIR}/${asset_name}"

  mkdir -p "${TOOLS_DIR}"
  echo "[setup_tools] Downloading ${url} ..."
  curl -fL --retry 3 --retry-delay 2 -o "${archive_path}.part" "${url}"
  mv "${archive_path}.part" "${archive_path}"

  echo "[setup_tools] Extracting ${asset_name} into ${TOOLS_DIR} ..."
  rm -rf "${OSS_CAD_DIR}"
  tar -xzf "${archive_path}" -C "${TOOLS_DIR}"
  rm -f "${archive_path}"

  if [[ ! -x "${OSS_CAD_DIR}/bin/verilator" ]]; then
    echo "ERROR: verilator not found after extracting oss-cad-suite" >&2
    exit 1
  fi
}

# Create `.tools/.venv` using `uv` and install the Python testbench (`tb/`)
# dependencies: pytest (test runner), cocotb (Python-to-Verilator bridge),
# and pyyaml (roadmap/config validation). Requires `uv` on PATH.
install_testbench_python_env() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' is required but not installed. Install from https://docs.astral.sh/uv/ and re-run." >&2
    exit 1
  fi

  if [[ -x "${VENV_DIR}/bin/pytest" ]] && "${VENV_DIR}/bin/python" -c "import cocotb, yaml" >/dev/null 2>&1; then
    echo "[setup_tools] Python testbench venv already ready at ${VENV_DIR}"
    return 0
  fi

  mkdir -p "${TOOLS_DIR}"
  echo "[setup_tools] Creating ${VENV_DIR} with uv (pytest + cocotb + pyyaml) ..."
  uv venv --allow-existing "${VENV_DIR}"
  uv pip install --python "${VENV_DIR}/bin/python" pytest cocotb pyyaml
}

# Generate `.tools/env.sh` so callers can source a single file to place all
# installed simulators, FPGA tools, and testbench Python tools onto PATH.
write_env_file() {
  cat > "${ENV_FILE}" <<EOF
# Source this file to put Apex simulators, FPGA tools, and cocotb/pytest on PATH:
#   source "${ENV_FILE}"
export APEX_TOOLS_DIR="${TOOLS_DIR}"
export PATH="${OSS_CAD_DIR}/bin:${VENV_DIR}/bin:\${PATH}"
EOF
  chmod +x "${ENV_FILE}"
}

# Source the generated env file and print installed versions to confirm every
# required binary and Python package resolves cleanly.
verify_tools() {
  # ENV_FILE is generated at runtime above; tell ShellCheck linter (SC1090) not to chase a dynamic path.
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  echo "[setup_tools] Tool versions:"
  echo "  verilator         : $(verilator --version | head -n 1)"
  echo "  yosys             : $(yosys -V | head -n 1)"
  echo "  nextpnr-himbaechel: $(nextpnr-himbaechel --version 2>&1 | head -n 1)"
  echo "  iverilog          : $(iverilog -V | head -n 1)"
  echo "  pytest            : $(pytest --version | head -n 1)"
  echo "  cocotb            : $("${VENV_DIR}/bin/python" -c 'import cocotb; print(cocotb.__version__)')"
}

install_oss_cad_suite
install_testbench_python_env
write_env_file
verify_tools

echo
echo "[setup_tools] Done. Run 'source ${ENV_FILE}' in your shell before invoking make/simulators."
