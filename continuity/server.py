"""Authenticated, pull-only HTTP transport. No shell endpoints or file browser.

A single adapter lock serializes native access. Disconnected viewers do not own
host processes. Tokens are memory-only and rotate whenever the service restarts.
"""
from __future__ import annotations
import hashlib
import ipaddress
import json
import re
import secrets
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from . import __version__
from .core import Problem, Session, FrameState, ImageBudget, compact, pack_frame, parse_roi


class Engine:
    def __init__(self, adapter, budget=5 * 1024 * 1024):
        self.adapter = adapter
        self.token = secrets.token_urlsafe(32)
        self.started = time.monotonic()
        self.sessions = {}
        self.lock = threading.RLock()
        self.budget = ImageBudget(budget)
        self.controller = ''
        self.lease_until = 0.0
        self.rx = self.tx = self.requests = 0
        self.revoked = False

    def revoke(self):
        with self.lock:
            self.revoked = True
            self.token = secrets.token_urlsafe(32)
            self.sessions.clear()
            self.controller = ''

    def session(self, key):
        if not re.fullmatch(r'[a-f0-9]{32}', key):
            raise Problem('client', '客户端标识无效', 400)
        now = time.monotonic()
        for k in list(self.sessions):
            if now - self.sessions[k].last_seen > 1800:
                del self.sessions[k]
        if key not in self.sessions:
            if len(self.sessions) >= 8:
                raise Problem('clients', '已达到 8 个访问端上限；请在 Mac 重启服务', 429)
            self.sessions[key] = Session()
        item = self.sessions[key]
        item.last_seen = now
        return item

    def target(self, session):
        if session.window is None:
            raise Problem('select', '请先选择现有窗口', 409)
        return self.adapter.ensure(session.window)

    def dispatch(self, client, path, data):
        with self.lock:
            if self.revoked:
                raise Problem('revoked', 'Host 已停止并撤销访问', 401)
            s = self.session(client)
            if path == '/api/status':
                return {'version': __version__, 'adapter': self.adapter.label,
                        'permissions': self.adapter.permissions(), 'window': s.window.public() if s.window else None,
                        'budget': self.budget.report(), 'traffic': {'rx_body': self.rx, 'tx_body': self.tx, 'requests': self.requests},
                        'control': self.controller == client and self.lease_until > time.monotonic(),
                        'note': '统计是所有访问端的 HTTP 正文，非运营商账单；无后台画面推送。'}
            if path == '/api/windows':
                return {'windows': [w.public() for w in self.adapter.windows()]}
            if path == '/api/select':
                wid = data.get('window')
                if isinstance(wid, bool) or not isinstance(wid, int):
                    raise Problem('invalid', '窗口标识必须是整数')
                target = next((w for w in self.adapter.windows() if w.id == wid), None)
                if target is None:
                    raise Problem('gone', '窗口已离开当前桌面', 409)
                s.window, s.frames, s.nodes = target, FrameState(), {}
                s.semantic_revision = ''
                return {'window': target.public()}
            if path == '/api/claim':
                now = time.monotonic()
                if self.controller not in ('', client) and self.lease_until > now:
                    raise Problem('controller', '另一访问端正在控制；请先在那边释放，或等 120 秒租约到期', 409)
                self.controller, self.lease_until = client, now + 120
                return {'control': True, 'expires_in': 120}
            if path == '/api/release':
                if self.controller == client:
                    self.controller, self.lease_until = '', 0
                return {'control': False}
            if path == '/api/frame':
                target = self.target(s)
                roi = parse_roi(data.get('roi', [0, 0, 1, 1]))
                image = self.adapter.capture(target)
                after = self.target(s)
                if after.bounds != target.bounds:
                    raise Problem('moved', '截图期间窗口移动了，请重新读取', 409)
                payload, candidate, header = pack_frame(image, s.frames, str(data.get('base', '')),
                    target.identity, target.bounds, width=data.get('width', 1024),
                    quality=data.get('quality', 55), roi=roi)
                self.budget.consume(len(payload))
                s.frames = candidate
                return payload
            if path == '/api/semantics':
                rows, handles, warnings = self.adapter.semantics(self.target(s))
                s.nodes, s.semantic_revision, s.semantic_time = handles, secrets.token_hex(12), time.monotonic()
                return {'revision': s.semantic_revision, 'nodes': rows, 'warnings': warnings,
                        'complete': False, 'scope': 'bounded accessibility projection, not full app state'}
            if path != '/api/action':
                raise Problem('not_found', '未知接口', 404)
            self.target(s)
            rid = data.get('request_id', '')
            if not isinstance(rid, str) or not re.fullmatch('[a-f0-9]{32}', rid):
                raise Problem('invalid', '操作需要唯一 request_id')
            digest = hashlib.sha256(compact(data)).hexdigest()
            if rid in s.responses:
                old_digest, result = s.responses[rid]
                if old_digest != digest:
                    raise Problem('request_id', '同一操作标识不得用于不同内容', 409)
                if isinstance(result, Problem):
                    raise result
                return dict(result, replay=True)
            if len(s.responses) >= 2048:
                raise Problem('action_limit', '本会话已达 2048 个操作，需在 Mac 重启服务；不清除去重记录后盲目重试', 429)
            if self.controller != client or self.lease_until <= time.monotonic():
                raise Problem('controller', '请先点“取得控制权”；控制租约 120 秒，每次操作续期', 409)
            self.lease_until = time.monotonic() + 120
            action = data.get('action')
            text = data.get('text', '')
            if not isinstance(text, str) or len(text) > 8000 or '\x00' in text:
                raise Problem('invalid', '文本超出 8000 字符或包含 NUL')
            s.responses[rid] = (digest, Problem('uncertain', '该操作已尝试，结果不确定；请先核对原窗口', 409))
            try:
                outcome = {}
                if action == 'activate':
                    self.adapter.activate(s.window)
                    s.frames = FrameState()
                elif data.get('mode') == 'semantic':
                    if data.get('revision') != s.semantic_revision or time.monotonic()-s.semantic_time > 60:
                        raise Problem('stale', '文字快照已过期，请重新读取', 409)
                    handle = s.nodes.get(str(data.get('node')))
                    if handle is None:
                        raise Problem('stale', '控件已失效，请重新读取', 409)
                    self.adapter.semantic_action(s.window, handle, action, text)
                    s.semantic_revision, s.nodes = '', {}
                    s.frames = FrameState()
                else:
                    if not s.frames.revision or data.get('revision') != s.frames.revision or time.monotonic()-s.frames.captured_at > 30:
                        raise Problem('stale', '画面已过期，请先刷新画面（有效期 30 秒）', 409)
                    outcome = self.adapter.visual_action(s.window, action, data, s.frames) or {}
                    s.frames.captured_at = 0
                    s.semantic_revision, s.nodes = '', {}
                result = {'ok': True, 'request_id': rid, 'replay': False, **outcome}
                s.responses[rid] = (digest, result)
                return result
            except Problem as error:
                s.responses[rid] = (digest, error)
                raise


class HostHTTP(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 8

    def __init__(self, address, engine, webroot, origins):
        self.engine, self.webroot = engine, Path(webroot)
        self.origins = set(origins)
        self.authorities = {urlsplit(o).netloc for o in self.origins}
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    server_version = 'WorkContinuity'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass

    def reply(self, status, payload, kind='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        with self.server.engine.lock:
            self.server.engine.tx += len(payload)
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def check_host(self):
        if self.headers.get('Host', '') not in self.server.authorities:
            raise Problem('host', 'Host 未获允许；反向代理需要显式配置 public origin', 403)
        origin = self.headers.get('Origin')
        if origin and origin not in self.server.origins:
            raise Problem('origin', '跨站请求已拒绝', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise Problem('origin', '跨站请求已拒绝', 403)

    def do_GET(self):
        try:
            self.check_host()
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if self.path not in files:
                raise Problem('not_found', 'Not found', 404)
            filename, kind = files[self.path]
            self.reply(200, (self.server.webroot/filename).read_bytes(), kind)
        except Problem as error:
            self.reply(error.status, compact({'error': error.code, 'message': error.message}))

    def do_POST(self):
        try:
            self.check_host()
            engine = self.server.engine
            if time.monotonic()-engine.started > 12*3600:
                raise Problem('expired', '服务密钥已过 12 小时有效期，请在 Mac 重启服务', 401)
            supplied = self.headers.get('Authorization', '').encode('utf-8')
            expected = ('Bearer '+engine.token).encode('utf-8')
            if not secrets.compare_digest(supplied, expected):
                raise Problem('auth', '连接密钥无效或已过期，请重新从 Mac 复制地址', 401)
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise Problem('length', '只接受一个 Content-Length', 400)
            try:
                length = int(self.headers['Content-Length'])
            except (ValueError, TypeError):
                raise Problem('length', '长度无效')
            if not 0 <= length <= 48*1024:
                raise Problem('size', '请求超过 48 KiB', 413)
            if self.headers.get_content_type() != 'application/json':
                raise Problem('content_type', '需要 JSON', 415)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise Problem('body', '请求不完整')
            try:
                data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite')))
            except (ValueError, UnicodeError):
                raise Problem('json', 'JSON 无效')
            if not isinstance(data, dict):
                raise Problem('json', '需要 JSON 对象')
            with engine.lock:
                engine.rx += len(raw)
                engine.requests += 1
            result = engine.dispatch(self.headers.get('X-WC-Client', ''), self.path, data)
            if isinstance(result, bytes):
                self.reply(200, result, 'application/vnd.work-continuity.tiles')
            else:
                self.reply(200, compact(result))
        except Problem as error:
            self.reply(error.status, compact({'error': error.code, 'message': error.message}))
        except Exception as error:
            self.reply(500, compact({'error': 'native_error', 'message': '原生操作异常（'+type(error).__name__+'）；请检查权限并核对原窗口。'}))


def make_server(adapter, webroot, host='127.0.0.1', port=8765, origins=None, budget=5*1024*1024,
                cert=None, key=None):
    origins = origins or [f'http://127.0.0.1:{port}', f'http://localhost:{port}']
    server = HostHTTP((host, port), Engine(adapter, budget), webroot, origins)
    if cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert, key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    return server
