#!/usr/bin/env bash
set -euo pipefail
#
# 将仓库内的「完整项目」同步到即将打入 Digital Dairy.app 的 app-runtime 目录。
# 这样用户从 DMG 安装后，在 App 包内即可访问全部源码与模板（数据与密钥仍在
# ~/Documents/DigitalDairy，见 UserLayout / DIGITAL_DAIRY_USER_HOME）。
#
# 用法：bundle_app_runtime.sh /path/to/.macos-app-runtime
#

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="${1:?请传入 app-runtime 目标目录，例如 ${ROOT_DIR}/.macos-app-runtime}"

rm -rf "$RUNTIME"
mkdir -p "$RUNTIME"

sync_dir() {
  local name="$1"
  [[ -d "${ROOT_DIR}/${name}" ]] || return 0
  rsync -a "${ROOT_DIR}/${name}/" "${RUNTIME}/${name}/"
}

# 管线运行所需 + 可选旧版桌面 / 资源
for d in scripts tools templates config app fig; do
  sync_dir "$d"
done

# Swift 原生壳源码（排除本地 SPM 构建缓存）
mkdir -p "${RUNTIME}/macOS"
rsync -a \
  --exclude='.build' \
  --exclude='.swiftpm' \
  "${ROOT_DIR}/macOS/DigitalDairyNative/" "${RUNTIME}/macOS/DigitalDairyNative/"

# data：只复制仓库内骨架（.gitkeep / README），避免把开发者本机 events/summaries 打进发行包
mkdir -p "${RUNTIME}/data"
for sub in events summaries replies visual inbox imports mobile health; do
  mkdir -p "${RUNTIME}/data/${sub}"
  [[ -f "${ROOT_DIR}/data/${sub}/.gitkeep" ]] && cp -f "${ROOT_DIR}/data/${sub}/.gitkeep" "${RUNTIME}/data/${sub}/" || true
  [[ -f "${ROOT_DIR}/data/${sub}/README.md" ]] && cp -f "${ROOT_DIR}/data/${sub}/README.md" "${RUNTIME}/data/${sub}/" || true
done

for f in README.md requirements.txt requirements-macos-app.txt setup.py; do
  [[ -f "${ROOT_DIR}/${f}" ]] && cp -f "${ROOT_DIR}/${f}" "${RUNTIME}/${f}" || true
done

find "$RUNTIME" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "app-runtime 已就绪: $RUNTIME"
