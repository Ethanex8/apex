#!/usr/bin/env bash
set -euo pipefail

# Install open-source RTL simulation and Gowin FPGA synthesis tools into .tools/
# (gitignored). Safe to re-run; skips downloads already present.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BRAIN_DIR}/../.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/.tools"
OSS_CAD_DIR="${TOOLS_DIR}/oss-cad-suite"
VENV_DIR="${TOOLS_DIR}/.venv"
ENV_FILE="${TOOLS_DIR}/env.sh"

PINNED_TAG="2026-11-12"
PINNED_STAMP="20261112"

detect_platform() {
  local uname_s uname_m os_part arch_part
  uname_s="$(uname -s)"
  uname_m="$(uname -m)"

  case "${uname_s}" in
    Linux)  os_part="linux" ;;
    Darwin) os_part="darwin" ;;
    *)
      echo "ERROR: Unsupported OS '${uname_s}'. Expected Linux or Darwin." >&2
      exit 1
      ;;
  esac

  case "${uname_m}" in
    x86_64|amd64)   arch_part="x64" ;;
    aarch64|arm64)  arch_part="arm64" ;;
    *)
      echo "ERROR: Unsupported CPU architecture '${uname_m}'." >&2
      exit 1
      ;;
  esac

  echo "${os_part}-${arch_part}"
}

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

install_python_tb_deps() {
  if [[ -x "${VENV_DIR}/bin/pytest" ]] && "${VENV_DIR}/bin/python" -c "import cocotb, yaml" >/dev/null 2>&1; then
    echo "[setup_tools] Python testbench venv already ready at ${VENV_DIR}"
    return 0
  fi

  mkdir -p "${TOOLS_DIR}"
  if command -v uv >/dev/null 2>&1; then
    echo "[setup_tools] Creating .tools/.venv with uv (pytest + cocotb + pyyaml) ..."
    uv venv --allow-existing "${VENV_DIR}"
    uv pip install --python "${VENV_DIR}/bin/python" pytest cocotb pyyaml
  else
    echo "[setup_tools] Creating .tools/.venv with python3 -m venv (pytest + cocotb + pyyaml) ..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install pytest cocotb pyyaml
  fi
}

write_env_file() {
  cat > "${ENV_FILE}" <<EOF
# Source this file to put Apex EDA simulators and cocotb/pytest on PATH:
#   source "${ENV_FILE}"
export APEX_TOOLS_DIR="${TOOLS_DIR}"
export PATH="${OSS_CAD_DIR}/bin:${VENV_DIR}/bin:\${PATH}"
EOF
  chmod +x "${ENV_FILE}"
}

verify_tools() {
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  echo "[setup_tools] Tool versions:"
  echo "  verilator        : $(verilator --version | head -n 1)"
  echo "  yosys            : $(yosys -V | head -n 1)"
  echo "  nextpnr-himbaechel: $(nextpnr-himbaechel --version 2>&1 | head -n 1)"
  echo "  iverilog         : $(iverilog -V | head -n 1)"
  echo "  pytest           : $(pytest --version | head -n 1)"
  echo "  cocotb           : $("${VENV_DIR}/bin/python" -c 'import cocotb; print(cocotb.__version__)')"
}

install_oss_cad_suite
install_python_tb_deps
write_env_file
verify_tools

echo
echo "[setup_tools] Done. Run 'source .tools/env.sh' in your shell before invoking make/simulators."
