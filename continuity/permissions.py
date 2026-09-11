"""Explicit, independent permission requests. No grants, resets or TCC writes.

Settings URLs are navigation hints, not a public guarantee of pane selection on
all macOS versions. Manual paths remain visible. Runtime paths stay on the Host
UI; they are never included in remote status or exported diagnostics.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class Permission:
    key: str
    title: str
    anchor: str
    request_selector: str
    settings_selector: str

    @property
    def settings_url(self) -> str:
        return 'x-apple.systempreferences:com.apple.preference.security?' + self.anchor


ACCESSIBILITY = Permission('accessibility', '辅助功能', 'Privacy_Accessibility',
                           'requestAccessibility:', 'openAccessibility:')
SCREEN_RECORDING = Permission('screen_recording', '录屏与系统录音', 'Privacy_ScreenCapture',
                              'requestScreenRecording:', 'openScreenRecording:')
PERMISSIONS = (ACCESSIBILITY, SCREEN_RECORDING)


def permission(key: str) -> Permission:
    for item in PERMISSIONS:
        if key == item.key:
            return item
    raise ValueError('Unknown permission: ' + str(key))


def request_permission(key: str, ax, quartz) -> bool:
    """Called only by an explicit native Host button, never remote HTTP.

    Return value is immediate system status, not proof that a list entry exists
    or that the user just granted permission. Do not chain the two prompts.
    """
    permission(key)  # Reject unknown permissions before doing anything.
    if key == ACCESSIBILITY.key:
        return bool(ax.AXIsProcessTrustedWithOptions({ax.kAXTrustedCheckOptionPrompt: True}))
    return bool(quartz.CGRequestScreenCaptureAccess())


def permission_hint(key: str, packaged: bool | None = None) -> str:
    item = permission(key)
    packaged = bool(getattr(sys, 'frozen', False)) if packaged is None else packaged
    if packaged:
        owner = ('请在 Mac Host 的对应权限行点“请求权限”。系统列表没有 WorkContinuity 时，'
                 '点“＋”添加 Host 显示的当前 WorkContinuity.app；授权后完整退出并重开。')
    else:
        owner = ('当前是源码启动，请在 Mac Host 的对应权限行请求权限；以系统弹窗显示的'
                 '启动终端或 Python 为授权对象。授权后完整退出并从相同方式重启。')
    return '当前 Host 的“' + item.title + '”权限尚未生效。' + owner


def runtime_identity(executable: str, frozen: bool, bundle_path: str = '', bundle_id: str = '') -> dict:
    """Describe the running program, not an invented or assumed install path.

    A bundle path is a location, NOT a claim about TCC's responsible-process
    attribution. Prefer the enclosing .app of the frozen executable.
    """
    app_path = ''
    if frozen:
        for parent in Path(executable).parents:
            if parent.suffix.lower() == '.app':
                app_path = str(parent)
                break
        if not app_path and Path(bundle_path).suffix.lower() == '.app':
            app_path = bundle_path
    return {'packaged': frozen, 'executable': executable, 'app_path': app_path,
            'bundle_id': bundle_id, 'reveal_path': app_path or executable}
