# Work Continuity 0.1.1 — input fix

修复画面右键和不可见的输入错误；默认后台控件，不主动置前；可明确选择后台定向键鼠实验模式。实验模式的“已提交”不等于应用已执行。系统菜单可能是独立窗口，当前单窗口截图未必包含。详情见 docs/INPUT-FIX.md 和附件验收说明。

Choose arm64 for Apple Silicon or x86_64 for Intel. Quit the previous Host, unzip and replace WorkContinuity.app in Applications, then reconnect using a fresh pairing URL. Python is bundled. macOS 13+ is the source target; CI builds run on macOS 14/15, not every OS version.

Ad-hoc signed, NOT Apple-notarized. LAN HTTP is opt-in and unencrypted; never publish the port on the Internet. Private HTTPS/VPN is required for untrusted networks. No automatic activation, approvals, unlocking or permission bypass in background routes.

Release publication requires protocol tests, Chromium/WebKit fixture interaction, native Mac event construction and UI launch, packaging and signature checks on both architectures. These do NOT prove real Lens/Codex/iPhone compatibility. CGEventPostToPid provides no application acknowledgement. Right-menu capture and arbitrary background input remain limited and must be assessed in a real host test.
