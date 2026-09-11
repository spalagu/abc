# Work Continuity · macOS Demo 0.1.1

**工具不用重做，工作能接续，远程流量可控。** 独立新项目，不依赖 Tabverse；仓库名 `abc` 暂作占位。

手机浏览器接入 Mac 已有窗口：文字/控件投影与按需局部画面连接同一份工作。没有复制应用、同步整个用户目录或默认视频流。

## 本次输入修复

旧版漏了右键且画面输入被前台限制挡住，错误还在视口外。0.1.1 接管开启操作时的画面右键、增加画面旁反馈，默认使用后台控件。可显式选择后台定向键鼠实验模式，但“已提交”不冒充“应用已执行”。不会自动激活应用；目标应用自身仍可能改变焦点。[具体改动与边界](docs/INPUT-FIX.md)

## 下载和更新

从 [Releases](https://github.com/spalagu/abc/releases) 下载最新成功构建的 prerelease：Apple 芯片选 `WorkContinuity-macOS-arm64.zip`，Intel 选 `WorkContinuity-macOS-x86_64.zip`。退出旧版，解压替换“应用程序”内的 WorkContinuity.app。Python 已包含。

应用仅 ad-hoc 签名，未 Apple 公证。核对自己的仓库和构建后，使用系统针对本应用的正常确认流程打开，不关闭系统安全功能。按 Host 提示授权辅助功能和屏幕录制；更新后可能需要重新授权、退出重开。

同一可信 Wi-Fi 下，明确勾选 LAN 模式，确认 HTTP 风险并启动，手机扫码选窗口。取得控制权、刷新、允许画面操作，**默认后台方式不需要手动置前**。HTTP 不加密，不可用于公共 Wi-Fi 或暴露公网；路上接入使用你自己的私有 HTTPS/VPN。

**[验收说明：概述、详细步骤与通过标准](docs/ACCEPTANCE.zh-CN.md)**

## 范围

| 能力 | 本版边界 |
|---|---|
| 原工作接续 | 使用现有窗口，网页断开不退出 Host 应用；不迁移进程、不承诺 Host 重启恢复 |
| 文字控件 | macOS Accessibility，有限遍历和不完整提示，不保证所有应用完整暴露信息 |
| 原画面 | 单窗口、ROI、128px JPEG 变化块，不用 Base64 传图；独立弹出菜单可能未被捕获 |
| 输入 | 默认后台 AX 控件；可选实验 PID 定向事件；前台兼容方式才要求目标已在前台 |
| 流量 | 默认手动更新，可明确开启前景网页 3 秒更新；Host 共享 5 MiB 画面正文预算 |
| 诊断 | 仅字节数、版本、权限布尔值、输入路径和错误码，不含密钥、图像或窗口内容 |

没有公网中继、专用终端字节通道、Codex 私有 API 适配、WASM、文件同步、进程迁移、连续音视频。这些是后续候选，不是禁止的技术。原生失败不会改用 fixture 或替代窗口。

## 源码启动与测试

macOS 13+、Python 3.11+，双击 Start-Mac.command，或：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m continuity --gui
```

依赖只装到项目 .venv。CLI 默认回环；`--lan` 明确开启可信 LAN；`--public-origin https://your-mac.example.ts.net` 允许你配置的 HTTPS 入口，后端仍回环监听。`--cert` 与 `--key` 可提供你自己的 TLS 证书。

```bash
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m pip install playwright==1.55.0
python3 -m playwright install chromium webkit
python3 tests/browser_smoke.py
python3 tests/browser_input.py
WC_BROWSER=webkit python3 tests/browser_input.py
# 以下在 Mac 执行
python3 -m pip install -r requirements-build.txt
bash scripts/build-macos.sh
```

CI：Linux 协议、Chromium/WebKit 浏览器交互 → 两种 Mac 架构原生事件构造、窗口启动、打包、签名验证 → 全通过才发布。浏览器使用合成适配器；原生事件测试不投递事件。**通过这些检查不代表 Lens/Codex/iPhone/VPN 实际后台输入验收通过。**

[测试范围](docs/TESTING.md) · [架构](docs/DESIGN.md) · [安全边界](docs/SECURITY.md)
