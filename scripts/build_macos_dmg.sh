#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="Digital Dairy.app"
DMG_NAME="Digital-Dairy.dmg"
DMG_STAGING="dist/dmg-staging"
VENV_DIR="${ROOT_DIR}/.venv-macos-app"
PYTHON_BIN="${VENV_DIR}/bin/python3"

if [[ ! -x "$PYTHON_BIN" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r requirements-macos-app.txt

rm -rf build dist

RUNTIME="${ROOT_DIR}/.macos-app-runtime"
rm -rf "$RUNTIME"
mkdir -p "$RUNTIME"
for d in scripts tools templates config; do
  rsync -a "${ROOT_DIR}/${d}/" "${RUNTIME}/${d}/"
done
find "$RUNTIME" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

"$PYTHON_BIN" setup.py py2app

rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "dist/$APP_NAME" "$DMG_STAGING/"
ln -sfn /Applications "$DMG_STAGING/Applications"

hdiutil create \
  -volname "Digital Dairy" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "dist/$DMG_NAME"

echo "DMG 已生成: $ROOT_DIR/dist/$DMG_NAME"
