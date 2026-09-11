# Work Continuity 0.1.2 — permission onboarding fix

修复授权入口混在一起的问题：辅助功能与录屏各有独立“请求权限”和“打开对应设置”按钮。显示当前运行应用路径、当前进程权限状态，新增 Finder 定位及重新检查；打包应用不再错误提示用户给 Terminal/Python 授权。没有录屏条目时，明确提示用对应列表的“＋”添加当前 .app。

This release does NOT claim to fix ad-hoc signing identity across upgrades or automatically grant permissions. No TCC resets, database edits or permission bypasses are performed. Settings deep links are best-effort; a manual path is always displayed.

Quit the previous Host, replace WorkContinuity.app, open the new version and use the new pairing URL. Choose arm64 for Apple Silicon or x86_64 for Intel. Python is bundled. Confirm 0.1.2-demo in the Host title and connected webpage. Existing apps and work are not terminated.

Missing entry: in System Settings > Privacy & Security > Screen & System Audio Recording, use the + under the upper list to add the exact running WorkContinuity.app, NOT under System Audio Recording Only. Grant access yourself, then quit and reopen Host. Current 0.1.1 users can also perform this manual recovery without updating.

Ad-hoc signed, NOT Apple-notarized. LAN HTTP is opt-in and unencrypted; never expose publicly. Input fixes from 0.1.1 are preserved. Background input acceptance and independent context-menu capture remain application-dependent.

Release gates: existing protocol and Chromium/WebKit regressions; 12 new permission-routing tests; native Mac buttons/UI, native event construction, packaged identity and signature checks on both architectures. These are NOT real-user TCC consent, Lens/Codex or iPhone acceptance tests.
