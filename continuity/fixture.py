"""EXPLICIT test adapter; never selected as a fallback on a real Mac."""
from __future__ import annotations
from PIL import Image, ImageDraw
from .core import Window, Problem


class FixtureAdapter:
    label = 'TEST FIXTURE — 不是你的 Mac'

    def __init__(self):
        self.value = 'A draft that remains on the host.'
        self.clicks = 0
        self.window = Window(101, 123, 'fixture-birth', 'TEST FIXTURE', 'Synthetic work', (0, 0, 960, 640))

    def permissions(self):
        return {'accessibility': True, 'screen_recording': True, 'fixture': True}

    def windows(self):
        return [self.window]

    def ensure(self, window):
        if window.identity != self.window.identity:
            raise Problem('gone', '测试窗口已退出', 409)
        return self.window

    def activate(self, window):
        self.ensure(window)

    def capture(self, window):
        self.ensure(window)
        image = Image.new('RGB', (960, 640), '#f7f9fb')
        draw = ImageDraw.Draw(image)
        draw.rectangle((24, 24, 936, 140), fill='#d5e9ff')
        draw.text((40, 44), 'TEST FIXTURE / NOT A REAL MAC WINDOW', fill='black')
        draw.text((40, 78), self.value, fill='black')
        draw.text((40, 170), 'Actions: ' + str(self.clicks), fill='black')
        return image

    def semantics(self, window):
        self.ensure(window)
        n = [
            {'id': '0', 'role': 'AXStaticText', 'label': 'TEST FIXTURE', 'value': '', 'editable': False, 'pressable': False, 'enabled': True, 'depth': 0},
            {'id': '1', 'role': 'AXTextArea', 'label': 'Draft', 'value': self.value, 'editable': True, 'pressable': False, 'enabled': True, 'depth': 0},
            {'id': '2', 'role': 'AXButton', 'label': 'Increment', 'value': str(self.clicks), 'editable': False, 'pressable': True, 'enabled': True, 'depth': 0},
        ]
        handles = {x['id']: (x['id'], x.copy()) for x in n}
        return n, handles, ['测试数据，不代表 macOS AX/Codex 兼容性。']

    def semantic_action(self, window, handle, action, text):
        self.ensure(window)
        key, old = handle
        if key == '1' and action == 'set':
            if old['value'] != self.value:
                raise Problem('stale', '内容已变化，请重新读取', 409)
            self.value = text
        elif key == '2' and action == 'press':
            if old['value'] != str(self.clicks):
                raise Problem('stale', '控件已变化', 409)
            self.clicks += 1
        else:
            raise Problem('unsupported', '不支持的操作')

    def visual_action(self, window, action, data, frame):
        self.ensure(window)
        if action == 'text':
            self.value += data['text']
        elif action in ('click', 'key', 'scroll'):
            self.clicks += 1
        else:
            raise Problem('unsupported', '不支持的操作')
