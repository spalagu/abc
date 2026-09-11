"""Background-first input. Public AX operations; explicit experimental PID events.

Never activate/raise an app or fall back to global input in background routes.
CGEventPostToPid has no application-level acknowledgement. Window fields are
hints, not a window-routing guarantee, so its route also checks AXFocusedWindow.
Frameworks are injected in unit tests; mock tests are not native compatibility.
"""
from __future__ import annotations
import time
from .core import Problem, bounded_number


def click_button(data):
    button = data.get('button', 'left')
    if not isinstance(button, str) or button not in ('left', 'right'):
        raise Problem('button', '仅支持左键或右键')
    return button


def screen_point(window, frame, data):
    x = bounded_number(data.get('x'), 0, 1, 'x')
    y = bounded_number(data.get('y'), 0, 1, 'y')
    rx, ry, rw, rh = frame.roi
    bx, by, bw, bh = window.bounds
    return (bx + min(bw-1, (rx+x*rw)*bw), by + min(bh-1, (ry+y*rh)*bh))


class WindowInput:
    def __init__(self, adapter, ax=None, quartz=None, cocoa=None):
        if ax is None:
            import ApplicationServices as ax
            import Quartz as quartz
            import AppKit as cocoa
        self.adapter, self.ax, self.q, self.k = adapter, ax, quartz, cocoa

    def get(self, element, name, default=None):
        return self.adapter._get(element, name, default)

    def belongs(self, element, target):
        for _ in range(24):
            if element is None:
                return False
            if element == target:
                return True
            element = self.get(element, 'AXParent')
        return False

    def secure(self, element, target):
        for _ in range(24):
            if element is None:
                return True  # missing ancestry is not a safe text target
            if 'Secure' in str(self.get(element, 'AXRole', '')) + str(self.get(element, 'AXSubrole', '')):
                return True
            if element == target:
                return False
            element = self.get(element, 'AXParent')
        return True

    def focused(self, root, target):
        element = self.get(root, 'AXFocusedUIElement')
        if element is None or not self.belongs(element, target) or self.secure(element, target):
            raise Problem('background_target', '未确认所选窗口内有安全的聚焦控件；未发送输入。', 409)
        return element

    def perform(self, window, action, data, frame):
        route = data.get('input_route', 'background')
        if route not in ('background', 'direct', 'foreground'):
            raise Problem('input_route', '未知输入方式')
        if action not in ('click', 'text', 'key', 'scroll'):
            raise Problem('unsupported', '未知输入动作')
        if action == 'click':
            click_button(data)
        current = self.adapter.ensure(window)
        if current.bounds != frame.bounds:
            raise Problem('moved', '窗口位置或大小已变化；未执行，请重新取画面', 409)
        if not self.ax.AXIsProcessTrusted():
            raise Problem('accessibility', '缺少辅助功能权限，请授权实际运行的 WorkContinuity / Terminal / Python', 403)
        before = self.k.NSWorkspace.sharedWorkspace().frontmostApplication()
        before_pid = int(before.processIdentifier()) if before else None
        if route == 'foreground':
            # Explicit legacy route; never activates the window on the user's behalf.
            self.adapter._frontmost(window)
            result = self.events(current, action, data, frame, directed=False)
        else:
            root, target = self.adapter._ax_window(current)
            if route == 'background':
                result = self.semantic(root, target, current, action, data, frame)
            else:
                if self.get(root, 'AXFocusedWindow') != target:
                    raise Problem('background_target', '无法确认进程的活动窗口就是所选窗口，未定向投递。请用后台控件方式；不会自动置前。', 409)
                if action in ('key', 'text'):
                    self.focused(root, target)
                result = self.events(current, action, data, frame, directed=True)
        # Do not restore/steal focus. Target apps can independently change focus.
        after = self.k.NSWorkspace.sharedWorkspace().frontmostApplication()
        after_pid = int(after.processIdentifier()) if after else None
        result['foreground_changed'] = before_pid != after_pid
        if result['foreground_changed']:
            result['message'] += ' 检测到前台进程变化；本程序未调用激活/置前，但应用自身或本地操作可能改变焦点。'
        return result

    def semantic(self, root, target, window, action, data, frame):
        a = self.ax
        if action == 'click':
            point = screen_point(window, frame, data)
            error, element = a.AXUIElementCopyElementAtPosition(root, *point, None)
            if error != 0 or element is None or not self.belongs(element, target):
                raise Problem('background_unsupported', '没有命中所选窗口内的后台控件；未点击。可显式选择“后台定向键鼠（实验）”测试，或读取文字控件；不会抢前台。', 409)
            if self.secure(element, target):
                raise Problem('secure', '安全控件不支持此后台操作', 403)
            requested = 'AXShowMenu' if click_button(data) == 'right' else 'AXPress'
            # Only follow the actual hit element's ancestors in the selected window.
            for _ in range(24):
                if element is None or element == target:
                    break
                code, names = a.AXUIElementCopyActionNames(element, None)
                if code == 0 and requested in (names or []):
                    if not self.get(element, 'AXEnabled', True):
                        raise Problem('disabled', '该控件已禁用；未操作', 409)
                    code = a.AXUIElementPerformAction(element, requested)
                    if code != 0:
                        raise Problem('ax_action', '控件操作已尝试，但应用未确认完成；请核对，未自动重试或改发键鼠。', 409)
                    return {'delivery': 'ax_acknowledged', 'route': 'background-ax',
                            'message': '后台控件接口已返回成功（'+requested+'）；请核对原窗口结果。' +
                                       (' 菜单可能是独立窗口，单窗口截图未必包含它。' if requested == 'AXShowMenu' else '')}
                element = self.get(element, 'AXParent')
        elif action == 'text':
            element = self.focused(root, target)
            code, can_set = a.AXUIElementIsAttributeSettable(element, 'AXSelectedText', None)
            if code == 0 and can_set:
                code = a.AXUIElementSetAttributeValue(element, 'AXSelectedText', data['text'])
                if code != 0:
                    raise Problem('ax_action', '文本操作已尝试但应用未确认；请核对，未改发键盘事件。', 409)
                return {'delivery': 'ax_acknowledged', 'route': 'background-ax',
                        'message': '后台控件接口已接受插入文本；请核对原输入框。'}
        raise Problem('background_unsupported', '应用没有为此处/此操作提供后台控件能力，未执行。可显式选“后台定向键鼠（实验）”；它仍不保证应用执行，不会自动置前。', 409)

    def events(self, window, action, data, frame, directed):
        q = self.q
        source = q.CGEventSourceCreate(q.kCGEventSourceStatePrivate)
        events = []
        if action == 'click':
            point = screen_point(window, frame, data)
            right = click_button(data) == 'right'
            button = q.kCGMouseButtonRight if right else q.kCGMouseButtonLeft
            kinds = (q.kCGEventRightMouseDown, q.kCGEventRightMouseUp) if right else (q.kCGEventLeftMouseDown, q.kCGEventLeftMouseUp)
            for kind in kinds:
                event = q.CGEventCreateMouseEvent(source, kind, point, button)
                if event is None:
                    raise Problem('event', '无法创建鼠标事件；未投递', 503)
                q.CGEventSetFlags(event, 0)
                q.CGEventSetIntegerValueField(event, q.kCGMouseEventClickState, 1)
                if directed:
                    q.CGEventSetIntegerValueField(event, q.kCGMouseEventWindowUnderMousePointer, window.id)
                    q.CGEventSetIntegerValueField(event, q.kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent, window.id)
                events.append(event)
        elif action == 'text':
            for start in range(0, len(data['text']), 40):
                text = data['text'][start:start+40]
                for down in (True, False):
                    event = q.CGEventCreateKeyboardEvent(source, 0, down)
                    q.CGEventSetFlags(event, 0)
                    q.CGEventKeyboardSetUnicodeString(event, len(text.encode('utf-16-le'))//2, text)
                    events.append(event)
        elif action == 'key':
            keys = {'enter': (36, 0), 'tab': (48, 0), 'escape': (53, 0), 'backspace': (51, 0),
                    'up': (126, 0), 'down': (125, 0), 'left': (123, 0), 'right': (124, 0),
                    'select_all': (0, q.kCGEventFlagMaskCommand), 'copy': (8, q.kCGEventFlagMaskCommand),
                    'interrupt': (8, q.kCGEventFlagMaskControl)}
            key = data.get('key')
            if not isinstance(key, str) or key not in keys:
                raise Problem('key', '不支持此快捷键')
            code, flags = keys[key]
            for down in (True, False):
                event = q.CGEventCreateKeyboardEvent(source, code, down)
                q.CGEventSetFlags(event, flags)
                events.append(event)
        else:
            delta = int(bounded_number(data.get('delta'), -8, 8, 'delta'))
            event = q.CGEventCreateScrollWheelEvent(source, q.kCGScrollEventUnitLine, 1, delta)
            q.CGEventSetLocation(event, screen_point(window, frame, {'x': .5, 'y': .5}))
            q.CGEventSetFlags(event, 0)
            events.append(event)
        # Revalidate before the first side effect. Never deliver down without building up.
        check = self.adapter.ensure(window)
        if check.bounds != frame.bounds:
            raise Problem('moved', '窗口在事件准备期间移动；未投递', 409)
        if directed:
            root, target = self.adapter._ax_window(check)
            if self.get(root, 'AXFocusedWindow') != target:
                raise Problem('background_target', '事件准备期间目标活动窗口变化；未投递', 409)
        else:
            self.adapter._frontmost(window)
        for event in events:
            if directed:
                q.CGEventPostToPid(window.pid, event)
            else:
                q.CGEventPost(q.kCGHIDEventTap, event)
            time.sleep(.02)
        return {'delivery': 'submitted_unconfirmed', 'route': 'pid-experimental' if directed else 'foreground-events',
                'message': '键鼠事件已提交给目标进程；系统不返回应用执行回执，不能据此认定点击成功。请看刷新结果，不自动重试。' +
                           (' 右键菜单可能是独立窗口，单窗口截图未必包含。' if action == 'click' and click_button(data) == 'right' else '')}
