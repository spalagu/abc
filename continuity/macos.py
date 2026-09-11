"""Native macOS adapter. Uses public AX, Quartz and screencapture interfaces.

This module is intentionally imported only on macOS. A failed native operation
raises an explicit error: it never substitutes fixture data or another window.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
import time
from pathlib import Path
from PIL import Image
import AppKit as K
import ApplicationServices as A
import Quartz as Q
from .core import Problem, Window, bounded_number


class MacAdapter:
    label = 'macOS 原生窗口'

    def permissions(self):
        return {'accessibility': bool(A.AXIsProcessTrusted()),
                'screen_recording': bool(Q.CGPreflightScreenCaptureAccess()),
                'fixture': False}

    def request_permissions(self):
        A.AXIsProcessTrustedWithOptions({A.kAXTrustedCheckOptionPrompt: True})
        Q.CGRequestScreenCaptureAccess()

    def _unlocked(self):
        state = Q.CGSessionCopyCurrentDictionary()
        if not state or state.get('CGSSessionScreenIsLocked', False) or not state.get('kCGSessionOnConsoleKey', True):
            raise Problem('locked', 'Mac 已锁定或没有活动图形会话；请在 Mac 解锁后重试', 423)

    def windows(self):
        self._unlocked()
        rows = Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionOnScreenOnly | Q.kCGWindowListExcludeDesktopElements, Q.kCGNullWindowID) or []
        result = []
        for item in rows:
            if int(item.get('kCGWindowLayer', 0)) != 0:
                continue
            b = item.get('kCGWindowBounds', {})
            if float(b.get('Width', 0)) < 100 or float(b.get('Height', 0)) < 70:
                continue
            pid = int(item['kCGWindowOwnerPID'])
            app = K.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app is None or app.isTerminated():
                continue
            date = app.launchDate()
            # Launch identity prevents a stale view from controlling a recycled PID.
            birth = str(date.timeIntervalSince1970()) if date else ''
            if not birth:
                continue
            bounds = tuple(float(b[k]) for k in ('X', 'Y', 'Width', 'Height'))
            result.append(Window(int(item['kCGWindowNumber']), pid, birth,
                                 str(item.get('kCGWindowOwnerName', 'App'))[:200],
                                 str(item.get('kCGWindowName', ''))[:1000], bounds))
        return result

    def ensure(self, window):
        current = next((w for w in self.windows() if w.id == window.id), None)
        if current is None or current.identity != window.identity:
            raise Problem('gone', '原窗口已关闭、隐藏或不在当前桌面；请重新选择，未接入替代窗口', 409)
        return current

    @staticmethod
    def _get(element, name, default=None):
        try:
            error, value = A.AXUIElementCopyAttributeValue(element, name, None)
            return value if error == 0 and value is not None else default
        except (ValueError, TypeError):
            return default

    def _ax_window(self, window):
        if not A.AXIsProcessTrusted():
            raise Problem('accessibility', '缺少辅助功能权限。请在 Mac 系统设置授权启动本程序的 Terminal/Python，然后重启 demo。', 403)
        current = self.ensure(window)
        root = A.AXUIElementCreateApplication(window.pid)
        A.AXUIElementSetMessagingTimeout(root, 0.15)
        candidates = self._get(root, 'AXWindows', [])
        matches = [w for w in candidates if str(self._get(w, 'AXTitle', '')) == current.title and current.title]
        if len(matches) == 1:
            return root, matches[0]
        if len(candidates) == 1 and (not current.title or str(self._get(candidates[0], 'AXTitle', '')) == current.title):
            return root, candidates[0]
        raise Problem('ax_window', '无法唯一对应这个窗口的控件树。请保留一个窗口或使用原画面；不会读取其他窗口代替。', 409)

    def activate(self, window):
        _, target = self._ax_window(window)
        app = K.NSRunningApplication.runningApplicationWithProcessIdentifier_(window.pid)
        if not app.activateWithOptions_(K.NSApplicationActivateIgnoringOtherApps):
            raise Problem('activate', '应用无法切到前台，请在 Mac 手动选择目标窗口', 409)
        code = A.AXUIElementPerformAction(target, 'AXRaise')
        if code != 0:
            raise Problem('activate', '窗口不支持置前，请在 Mac 手动选择目标窗口', 409)
        time.sleep(.15)

    def capture(self, window):
        self.ensure(window)
        if not Q.CGPreflightScreenCaptureAccess():
            raise Problem('screen_recording', '缺少屏幕录制权限。请在 Mac 系统设置授权实际出现的 Terminal/Python 进程，然后重启 demo。', 403)
        with tempfile.TemporaryDirectory(prefix='work-continuity-') as directory:
            path = Path(directory) / 'window.png'
            try:
                proc = subprocess.run(['/usr/sbin/screencapture', '-x', '-o', '-l', str(window.id), '-t', 'png', str(path)],
                                      capture_output=True, timeout=8, check=False)
            except subprocess.TimeoutExpired:
                raise Problem('capture_timeout', '截图超时，请检查权限并缩小窗口', 504)
            if proc.returncode != 0 or not path.exists() or path.stat().st_size == 0:
                raise Problem('capture', '系统未返回此窗口画面；请检查屏幕录制权限和窗口状态', 503)
            with Image.open(path) as image:
                image.load()
                return image.convert('RGB')

    @staticmethod
    def _text(value, limit=8000):
        if value is None:
            return ''
        if isinstance(value, (str, int, float, bool)):
            return str(value)[:limit]
        return ''

    def _describe(self, element, key, depth):
        role = self._text(self._get(element, 'AXRole'), 120)
        subrole = self._text(self._get(element, 'AXSubrole'), 120)
        secure = 'Secure' in role or 'Secure' in subrole
        label = self._text(self._get(element, 'AXTitle'), 1000) or self._text(self._get(element, 'AXDescription'), 1000)
        value = '' if secure else self._text(self._get(element, 'AXValue'))
        actions = []
        try:
            error, names = A.AXUIElementCopyActionNames(element, None)
            if error == 0:
                actions = [str(x) for x in (names or [])]
        except (TypeError, ValueError):
            pass
        editable = False
        if not secure and role in ('AXTextField', 'AXTextArea', 'AXComboBox'):
            error, editable = A.AXUIElementIsAttributeSettable(element, 'AXValue', None)
            editable = error == 0 and bool(editable)
        return {'id': key, 'role': role, 'label': '[密码控件已隐藏]' if secure else label,
                'value': value, 'editable': editable, 'pressable': 'AXPress' in actions and not secure,
                'enabled': bool(self._get(element, 'AXEnabled', True)), 'depth': depth, 'secure': secure}

    def semantics(self, window):
        _, target = self._ax_window(window)
        rows, handles, warnings = [], {}, []
        todo = [(target, '0', 0)]
        scanned, chars = 0, 0
        deadline = time.monotonic() + 3.0
        while todo and scanned < 600 and chars < 120_000 and time.monotonic() < deadline:
            element, key, depth = todo.pop()
            scanned += 1
            row = self._describe(element, key, depth)
            meaningful = row['value'] or row['label'] or row['editable'] or row['pressable']
            if meaningful:
                rows.append(row)
                handles[key] = (element, row.copy())
                chars += len(row['label']) + len(row['value'])
            if row['secure']:
                continue
            if depth < 20:
                children = self._get(element, 'AXChildren', [])
                for i, child in reversed(list(enumerate(children[:600]))):
                    todo.append((child, key + '.' + str(i), depth + 1))
            else:
                warnings.append('部分嵌套超过 20 层，未读取。')
        if todo:
            warnings.append('达到遍历时间、节点或文本上限；这是部分内容，不是完整窗口。')
        if not rows:
            warnings.append('应用没有提供可读控件，请切换原画面。')
        warnings.append('语义模式可能遗漏 Canvas、图表和自绘内容；需要核对时查看原画面。')
        return rows, handles, list(dict.fromkeys(warnings))

    def semantic_action(self, window, handle, action, text):
        self.ensure(window)
        element, old = handle
        code, pid = A.AXUIElementGetPid(element, None)
        if code != 0 or int(pid) != window.pid:
            raise Problem('stale', '控件归属已失效，请重新读取', 409)
        fresh = self._describe(element, old['id'], old['depth'])
        for name in ('role', 'label', 'value', 'enabled', 'editable', 'pressable', 'secure'):
            if fresh[name] != old[name]:
                raise Problem('stale', '控件内容或状态已变化；请重新读取，未执行旧操作', 409)
        if fresh['secure'] or not fresh['enabled']:
            raise Problem('unsupported', '该控件禁止远程操作', 403)
        if action == 'set' and fresh['editable']:
            result = A.AXUIElementSetAttributeValue(element, 'AXValue', text)
        elif action == 'press' and fresh['pressable']:
            result = A.AXUIElementPerformAction(element, 'AXPress')
        else:
            raise Problem('unsupported', '控件未声明支持此操作', 409)
        if result != 0:
            raise Problem('ax_action', '系统未确认操作成功；请查看原界面，不要盲目重试', 409)

    def _frontmost(self, window):
        self._unlocked()
        current = self.ensure(window)
        app = K.NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None or int(app.processIdentifier()) != window.pid:
            raise Problem('not_frontmost', '目标应用不在前台，请先点“将目标窗口置前”', 409)
        visible = self.windows()
        if not visible or visible[0].id != window.id:
            raise Problem('not_frontmost', '目标不是最前面的窗口，请先置前并刷新；未发送全局输入', 409)
        return current

    def visual_action(self, window, action, data, frame):
        from .window_input import WindowInput
        return WindowInput(self).perform(window, action, data, frame)
