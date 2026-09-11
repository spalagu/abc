#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname -s)" = Darwin ] || { echo 'Build on macOS'; exit 1; }
python3 -m PyInstaller --noconfirm --clean --windowed --onedir --name WorkContinuity \
  --osx-bundle-identifier io.github.spalagu.workcontinuity \
  --add-data 'web:web' --hidden-import AppKit --hidden-import Foundation \
  --hidden-import Quartz --hidden-import ApplicationServices --hidden-import qrcode.image.pil host.py
python3 - <<'PY'
import plistlib
p='dist/WorkContinuity.app/Contents/Info.plist'
with open(p,'rb') as f: d=plistlib.load(f)
d.update(CFBundleShortVersionString='0.1.2',CFBundleVersion='3',LSMinimumSystemVersion='13.0',
         NSHighResolutionCapable=True,
         NSLocalNetworkUsageDescription='Connect your own phone to this Mac on a trusted local network.')
with open(p,'wb') as f: plistlib.dump(d,f)
PY
codesign --force --deep --sign - dist/WorkContinuity.app
codesign --verify --deep --strict dist/WorkContinuity.app
dist/WorkContinuity.app/Contents/MacOS/WorkContinuity --smoke-test
mkdir -p release
ARCH="$(uname -m)"
cp docs/ACCEPTANCE.zh-CN.md release/START-HERE.zh-CN.md
cp docs/SECURITY.md release/SECURITY.md
cp dist/WorkContinuity.app/Contents/Info.plist release/Info.plist
python3 -m pip freeze > release/dependencies.txt
ditto -c -k --sequesterRsrc --keepParent dist/WorkContinuity.app "release/WorkContinuity-macOS-${ARCH}.zip"
(cd release && shasum -a 256 WorkContinuity-*.zip > SHA256SUMS-${ARCH}.txt)
