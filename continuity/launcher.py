"""Source CLI and a small native macOS host window; no cloud account required."""
from __future__ import annotations
import argparse
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import webbrowser
from .server import make_server


def webroot():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'web'


def local_ips():
    found = []
    if sys.platform == 'darwin':
        for iface in ('en0', 'en1'):
            p = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', iface], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                found.append(p.stdout.strip())
        p = subprocess.run(['/sbin/ifconfig'], capture_output=True, text=True, timeout=3)
        found += re.findall(r'\binet (\d+\.\d+\.\d+\.\d+)', p.stdout)
    else:
        try:
            found += socket.gethostbyname_ex(socket.gethostname())[2]
        except OSError:
            pass
    valid = []
    for item in found:
        try:
            address = ipaddress.ip_address(item)
            allowed = (address in ipaddress.ip_network('10.0.0.0/8') or
                       address in ipaddress.ip_network('172.16.0.0/12') or
                       address in ipaddress.ip_network('192.168.0.0/16') or
                       address in ipaddress.ip_network('100.64.0.0/10'))
            if allowed and item not in valid:
                valid.append(item)
        except ValueError:
            pass
    return valid


def public_origin(value):
    if not value:
        return ''
    parsed = urlsplit(value.strip().rstrip('/'))
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError('外部地址必须是 HTTPS origin，例如 https://mac.example.ts.net；不含路径或密钥。')
    return parsed.geturl()


def native_gui():
    import AppKit as K
    import Foundation as F
    from PyObjCTools import AppHelper
    from .macos import MacAdapter

    class HostDelegate(F.NSObject):
        def applicationDidFinishLaunching_(self, notification):
            self.server = None
            self.join = ''
            self.adapter = MacAdapter()
            self.window = K.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                ((0, 0), (720, 610)), K.NSWindowStyleMaskTitled | K.NSWindowStyleMaskClosable | K.NSWindowStyleMaskMiniaturizable,
                K.NSBackingStoreBuffered, False)
            self.window.setTitle_('Work Continuity · 独立可行性 Demo')
            self.window.center()
            content = self.window.contentView()
            def label(text, rect, size=13):
                field = K.NSTextField.alloc().initWithFrame_(rect)
                field.setStringValue_(text)
                field.setEditable_(False); field.setBezeled_(False); field.setDrawsBackground_(False)
                field.setSelectable_(True); field.setFont_(K.NSFont.systemFontOfSize_(size))
                content.addSubview_(field)
                return field
            def button(text, action, rect):
                b = K.NSButton.alloc().initWithFrame_(rect)
                b.setTitle_(text); b.setTarget_(self); b.setAction_(action); b.setBezelStyle_(K.NSBezelStyleRounded)
                content.addSubview_(b)
                return b
            label('接着做。', ((24, 551), (500, 42)), 30)
            label('同一个 Mac 窗口 · 文字控件 / 按需局部画面 · 默认只监听本机', ((26, 514), (665, 32)))
            button('1. 请求辅助功能与屏幕录制权限', 'permissions:', ((24, 465), (315, 34)))
            button('打开系统隐私设置', 'settings:', ((350, 465), (220, 34)))
            self.lan = K.NSButton.alloc().initWithFrame_(((24, 415), (668, 32)))
            self.lan.setButtonType_(K.NSButtonTypeSwitch)
            self.lan.setTitle_('允许可信局域网连接（HTTP 明文，仅在自家 Wi-Fi 验证）')
            content.addSubview_(self.lan)
            label('可选：Tailscale Serve / 自有 HTTPS 代理地址（先配置代理，再填写）', ((26, 385), (660, 26)))
            self.external = K.NSTextField.alloc().initWithFrame_(((26, 348), (658, 30)))
            self.external.setPlaceholderString_('https://your-mac.your-tailnet.ts.net')
            content.addSubview_(self.external)
            button('2. 启动服务', 'start:', ((24, 296), (165, 36)))
            button('打开本机入口', 'openLocal:', ((197, 296), (165, 36)))
            button('复制连接地址', 'copyLink:', ((370, 296), (165, 36)))
            button('停止并撤销密钥', 'stop:', ((543, 296), (153, 36)))
            self.info = label('尚未启动。授权后需要退出并重新打开本应用。\n启动服务不会启动、复制或关闭你的工作软件。', ((26, 82), (435, 195)), 12)
            self.qr = K.NSImageView.alloc().initWithFrame_(((495, 82), (192, 192)))
            content.addSubview_(self.qr)
            label('预算：本轮所有客户端共享 5 MiB 画面正文。重启服务才重置。\n无公网中继，不绕过锁屏；合盖睡眠会中断连接。不要在公共 Wi-Fi 开启 HTTP。', ((26, 18), (665, 56)), 12)
            menu = K.NSMenu.alloc().init()
            item = K.NSMenuItem.alloc().init(); menu.addItem_(item)
            submenu = K.NSMenu.alloc().init()
            quititem = K.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('退出 Work Continuity', 'terminate:', 'q')
            submenu.addItem_(quititem); item.setSubmenu_(submenu)
            K.NSApplication.sharedApplication().setMainMenu_(menu)
            self.window.makeKeyAndOrderFront_(None)
            K.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

        def alert_(self, text):
            alert = K.NSAlert.alloc().init()
            alert.setMessageText_('Work Continuity')
            alert.setInformativeText_(text)
            alert.addButtonWithTitle_('确定')
            alert.runModal()

        def permissions_(self, sender):
            self.adapter.request_permissions()
            self.alert_('请在系统设置开启“辅助功能”和“屏幕与系统音频录制”中实际出现的 WorkContinuity。源码模式可能显示 Terminal/Python。授权后退出并重新打开。')

        def settings_(self, sender):
            K.NSWorkspace.sharedWorkspace().openURL_(F.NSURL.URLWithString_('x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'))

        def start_(self, sender):
            if self.server:
                self.alert_('服务已在运行。改网络配置前请先停止。')
                return
            try:
                external = public_origin(str(self.external.stringValue()))
                lan = self.lan.state() == K.NSControlStateValueOn
                if external and lan:
                    raise ValueError('使用 HTTPS 代理时请取消局域网明文选项，后端仅监听本机。')
                if lan:
                    alert = K.NSAlert.alloc().init()
                    alert.setMessageText_('仅用于可信局域网测试')
                    alert.setInformativeText_('HTTP 不加密画面、文字或密钥。不要端口转发到公网，不要在公共 Wi-Fi 使用。正式路上测试请使用私有 HTTPS / VPN。')
                    alert.addButtonWithTitle_('取消')
                    alert.addButtonWithTitle_('我在可信网络，继续测试')
                    if alert.runModal() != K.NSAlertSecondButtonReturn:
                        return
                ips = local_ips() if lan else []
                origins = ['http://127.0.0.1:8765', 'http://localhost:8765'] + [f'http://{ip}:8765' for ip in ips]
                if external:
                    origins.append(external)
                self.server = make_server(self.adapter, webroot(), '0.0.0.0' if lan else '127.0.0.1', 8765, origins)
                threading.Thread(target=self.server.serve_forever, daemon=True).start()
                origin = external or (f'http://{ips[0]}:8765' if ips else origins[0])
                self.join = origin + '/#token=' + self.server.engine.token
                local = 'http://127.0.0.1:8765/#token=' + self.server.engine.token
                self.info.setStringValue_('服务已启动。手机扫描右侧二维码。\n\n连接地址：\n'+self.join+'\n\n'+('未检测到局域网 IP，手机无法使用 127.0.0.1。' if lan and not ips else '本机入口始终是 127.0.0.1:8765。')+'\n密钥 12 小时有效；停止服务立即撤销。')
                import qrcode
                raw = io.BytesIO(); qrcode.make(self.join).save(raw, format='PNG')
                nsdata = F.NSData.dataWithBytes_length_(raw.getvalue(), len(raw.getvalue()))
                self.qr.setImage_(K.NSImage.alloc().initWithData_(nsdata))
                self.lan.setEnabled_(False); self.external.setEnabled_(False)
                webbrowser.open(local)
            except Exception as error:
                self.alert_('启动失败：'+str(error))

        def openLocal_(self, sender):
            if self.server:
                webbrowser.open('http://127.0.0.1:8765/#token='+self.server.engine.token)
            else:
                self.alert_('请先启动服务。')

        def copyLink_(self, sender):
            if not self.join:
                self.alert_('请先启动服务。')
                return
            board = K.NSPasteboard.generalPasteboard(); board.clearContents()
            board.setString_forType_(self.join, K.NSPasteboardTypeString)

        def stop_(self, sender):
            if self.server:
                self.server.engine.revoke(); self.server.shutdown(); self.server.server_close(); self.server = None
            self.join = ''
            self.qr.setImage_(None)
            self.info.setStringValue_('服务已停止，所有连接密钥失效。\n目标应用和任务没有被关闭。')
            self.lan.setEnabled_(True); self.external.setEnabled_(True)

        def applicationShouldTerminateAfterLastWindowClosed_(self, app):
            return True

        def applicationWillTerminate_(self, notification):
            if self.server:
                self.server.engine.revoke(); self.server.shutdown(); self.server.server_close()

    app = K.NSApplication.sharedApplication()
    app.setActivationPolicy_(K.NSApplicationActivationPolicyRegular)
    delegate = HostDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


def main():
    parser = argparse.ArgumentParser(description='Work Continuity experimental Mac host')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--fixture', action='store_true', help='explicit synthetic test adapter; NOT real work')
    parser.add_argument('--lan', action='store_true', help='EXPLICITLY allow trusted LAN HTTP; never expose to Internet')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--public-origin', default='')
    parser.add_argument('--budget-mib', type=float, default=5)
    parser.add_argument('--cert'); parser.add_argument('--key')
    parser.add_argument('--smoke-test', action='store_true')
    args = parser.parse_args()
    if args.smoke_test:
        assert (webroot()/'index.html').is_file()
        if sys.platform == 'darwin':
            from .macos import MacAdapter
            import ApplicationServices as A
            import Quartz as Q
            import AppKit as K
            import qrcode
            for name in ['AXUIElementCopyAttributeValue', 'AXUIElementGetPid', 'AXUIElementSetMessagingTimeout']:
                assert hasattr(A, name), name
            for name in ['CGPreflightScreenCaptureAccess', 'CGEventKeyboardSetUnicodeString']:
                assert hasattr(Q, name), name
            print(json.dumps({'mac_imports': True, 'permissions': MacAdapter().permissions()}))
        print('smoke-test: assets and imports OK; NOT an interactive permission/remote test')
        return
    if args.gui or (getattr(sys, 'frozen', False) and len(sys.argv) == 1):
        if sys.platform != 'darwin':
            parser.error('native GUI requires macOS')
        native_gui(); return
    if not 1 <= args.port <= 65535 or not 0.01 <= args.budget_mib <= 100:
        parser.error('port 1..65535; budget 0.01..100 MiB')
    if bool(args.cert) != bool(args.key):
        parser.error('--cert and --key must be used together')
    if args.fixture:
        from .fixture import FixtureAdapter
        adapter = FixtureAdapter()
    elif sys.platform == 'darwin':
        from .macos import MacAdapter
        adapter = MacAdapter()
    else:
        parser.error('real host currently requires macOS; --fixture is only for testing')
    scheme = 'https' if args.cert else 'http'
    origins = [f'{scheme}://127.0.0.1:{args.port}', f'{scheme}://localhost:{args.port}']
    if args.lan:
        origins += [f'{scheme}://{ip}:{args.port}' for ip in local_ips()]
        print('WARNING: LAN access explicitly enabled. No public port forwarding; HTTP is unencrypted.')
    if args.public_origin:
        origins.append(public_origin(args.public_origin))
    server = make_server(adapter, webroot(), '0.0.0.0' if args.lan else '127.0.0.1', args.port,
                         origins, int(args.budget_mib*1024*1024), args.cert, args.key)
    print(adapter.label)
    for origin in origins:
        print(origin+'/#token='+server.engine.token)
    print('Ctrl+C stops access only; existing host work is not terminated.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.engine.revoke()
        server.server_close()


if __name__ == '__main__':
    main()
