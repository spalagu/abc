# Work Continuity · macOS Demo

**工具不用重做，工作能接续，远程流量可控。** 独立新项目，不依赖 Tabverse。仓库名 `abc` 暂作占位。

手机浏览器接入 Mac 已有窗口：文字/控件投影与按需局部画面连接同一份工作。没有复制应用、同步整个用户目录或默认视频流。

## 下载

到 [Releases](https://github.com/spalagu/abc/releases) 下载最新成功构建的 prerelease：Apple 芯片选 `WorkContinuity-macOS-arm64.zip`，Intel 选 `WorkContinuity-macOS-x86_64.zip`。解压，将 WorkContinuity.app 放入“应用程序”。Python 已打包。

应用只有 ad-hoc 签名，未做 Apple Developer ID 公证。首次打开可能需要在系统“隐私与安全性”确认此应用；不要关闭系统整体安全检查。按 Host 提示授权辅助功能和屏幕录制，退出重开。

同一自家 Wi-Fi 下，明确勾选“允许可信局域网连接”，确认 HTTP 风险后启动；手机扫码，选窗口，读取文字或刷新画面，操作前取得控制权。**HTTP 不加密，不得暴露公网或用于公共 Wi-Fi。** 路上接入使用你自己的私有 HTTPS/VPN。

**[验收说明：概述、详细步骤与通过标准](docs/ACCEPTANCE.zh-CN.md)**

## 范围

| 能力 | 本版边界 |
|---|---|
| 原工作接续 | 使用已打开的窗口；网页断开不退出应用；不迁移进程、不承诺 Host 重启恢复 |
| 文字控件 | macOS Accessibility，有限遍历和显式不完整提示，不保证所有应用完整暴露信息 |
| 原画面 | 单窗口、ROI、128px JPEG 变化块、无 Base64 图像传输 |
| 输入 | 点击、Unicode 文本、有限快捷键和滚动；控制租约、近期快照、前台窗口校验 |
| 流量 | 默认手动更新；可显式开启 3 秒更新；隐藏网页停止；Host 共享 5 MiB 画面正文预算 |
| 诊断 | 只导出字节数、版本、权限布尔值与错误码，不含密钥、图像和窗口内容 |

未实现：公网中继、专用终端字节通道、Codex API 适配、WASM 系统、文件同步、运行迁移、连续音视频。它们是后续候选，不是被禁止的技术。原生失败不会静默改用 fixture 或其他窗口。

## 源码启动（备用）

macOS 13+、Python 3.11+。双击 `Start-Mac.command`，或：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m continuity --gui
```

只安装到项目 .venv，不更改系统 Python。CLI 默认回环；`--lan` 明确开启可信 LAN；`--public-origin https://your-mac.example.ts.net` 允许你配置的 HTTPS 入口，但后端仍回环监听。`--cert` 与 `--key` 可提供你自己的 TLS 证书。

## 测试与构建

```bash
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m pip install playwright==1.55.0
python3 -m playwright install chromium
python3 tests/browser_smoke.py
# 以下必须在 Mac 上执行
python3 -m pip install -r requirements-build.txt
bash scripts/build-macos.sh
```

CI：Linux 协议和浏览器测试 → Apple Silicon/Intel Mac 导入、打包、签名验证 → 全通过才发布 prerelease。PR 不发布；main 推送才发布，避免 branch 与 PR 双份流水线。

**自动测试与打包通过不等于你的 Mac、Codex、iPhone 或 VPN 的实际验收通过。** 浏览器自动测试使用明确的合成适配器。[测试范围](docs/TESTING.md) · [架构](docs/DESIGN.md) · [安全边界](docs/SECURITY.md)
