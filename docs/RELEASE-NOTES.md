# Work Continuity — experimental macOS demo

Choose **arm64** for Apple Silicon or **x86_64** for Intel. Unzip and move WorkContinuity.app to Applications. Python is bundled. macOS 13+ is the source target; CI builds are exercised on macOS 14 (Apple Silicon) and 15 (Intel), not every supported OS version.

Read the attached ACCEPTANCE.zh-CN.md first: installation, permissions, same-Wi-Fi validation, optional private HTTPS/Tailscale setup, pass criteria and troubleshooting.

Features: native existing-window selection; bounded AX text/controls; on-demand JPEG tile deltas and ROI; limited real input; expiring scenes and control lease; host-wide frame budget; content-free diagnostics. No Tabverse dependency.

**Important:** ad-hoc signed, not Apple-notarized. HTTP LAN mode is explicitly opt-in and unencrypted; never expose the port publicly. The app does not unlock the Mac, bypass permissions, keep it awake or operate a second copy of your work. No automatic approvals.

A published release means automated tests and packaging passed. It does **not** mean actual Mac/Codex/iPhone/VPN interactive acceptance passed. AX may be incomplete; original image mode is available for checking. All usage is experimental.
