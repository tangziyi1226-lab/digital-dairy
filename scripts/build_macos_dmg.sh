#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="Digital Dairy.app"
DMG_NAME="Digital-Dairy.dmg"
DMG_STAGING="dist/dmg-staging"
PKG_DIR="${ROOT_DIR}/macOS/DigitalDairyNative"
INFO_PLIST="${PKG_DIR}/Support/Info.plist"

if ! command -v swift >/dev/null 2>&1; then
  echo "未找到 swift：请安装 Xcode Command Line Tools 或 Xcode。" >&2
  exit 1
fi

rm -rf dist build
mkdir -p dist

RUNTIME="${ROOT_DIR}/.macos-app-runtime"
"${ROOT_DIR}/scripts/bundle_app_runtime.sh" "$RUNTIME"

# 先全量 clean 再编译，避免增量缓存导致 .app 仍是旧界面。
(
  cd "$PKG_DIR" || exit 1
  swift package clean
  swift build -c release
)
BIN_DIR="$(cd "$PKG_DIR" && swift build -c release --show-bin-path)"
EXE="${BIN_DIR}/DigitalDairyNative"
if [[ ! -x "$EXE" ]]; then
  echo "Swift 构建失败：未找到可执行文件 $EXE" >&2
  exit 1
fi

APP_PATH="dist/${APP_NAME}"
CONTENTS="${APP_PATH}/Contents"
mkdir -p "${CONTENTS}/MacOS" "${CONTENTS}/Resources"
cp -f "$EXE" "${CONTENTS}/MacOS/DigitalDairyNative"
chmod +x "${CONTENTS}/MacOS/DigitalDairyNative"
cp -f "$INFO_PLIST" "${CONTENTS}/Info.plist"
echo "APPL????" > "${CONTENTS}/PkgInfo"

rsync -a "${RUNTIME}/" "${CONTENTS}/Resources/app-runtime/"

rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_PATH" "$DMG_STAGING/"
ln -sfn /Applications "$DMG_STAGING/Applications"

hdiutil create \
  -volname "Digital Dairy" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "dist/$DMG_NAME"

echo "原生 SwiftUI .app 与 DMG 已生成: $ROOT_DIR/dist/$DMG_NAME"
