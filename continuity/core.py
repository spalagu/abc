"""Platform-independent protocol, state and bounded image transport.

Images use a 4-byte big-endian JSON-header length, the UTF-8 JSON header,
and concatenated JPEG tile bodies. No base64 in the network data plane.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import secrets
import struct
import time
from dataclasses import dataclass, field
from typing import Any
from PIL import Image


class Problem(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def compact(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def bounded_number(value: Any, lo: float, hi: float, name: str) -> float:
    if isinstance(value, bool):
        raise Problem('invalid', name + ' 必须是数字')
    try:
        x = float(value)
    except (ValueError, TypeError):
        raise Problem('invalid', name + ' 必须是数字')
    if not math.isfinite(x) or not lo <= x <= hi:
        raise Problem('invalid', name + ' 超出范围')
    return x


def parse_roi(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise Problem('invalid', 'ROI 必须是 [x,y,width,height]')
    x, y, w, h = (bounded_number(n, 0, 1, 'ROI') for n in value)
    if w < .1 or h < .1 or x + w > 1.00001 or y + h > 1.00001:
        raise Problem('invalid', 'ROI 超出窗口或小于 10%')
    return x, y, w, h


@dataclass(frozen=True)
class Window:
    id: int
    pid: int
    birth: str
    app: str
    title: str
    bounds: tuple[float, float, float, float]

    @property
    def identity(self) -> tuple:
        return self.id, self.pid, self.birth

    def public(self) -> dict:
        return {'id': self.id, 'app': self.app, 'title': self.title}


@dataclass
class FrameState:
    revision: str = ''
    key: tuple = ()
    hashes: dict = field(default_factory=dict)
    bounds: tuple = ()
    roi: tuple = (0, 0, 1, 1)
    captured_at: float = 0.0


@dataclass
class Session:
    window: Window | None = None
    frames: FrameState = field(default_factory=FrameState)
    nodes: dict = field(default_factory=dict)
    semantic_revision: str = ''
    semantic_time: float = 0.0
    responses: dict = field(default_factory=dict)
    last_seen: float = field(default_factory=time.monotonic)


def pack_frame(image: Image.Image, previous: FrameState, base: str,
               identity: tuple, bounds: tuple, width: int = 1024,
               quality: int = 55, roi: tuple = (0, 0, 1, 1),
               tile_size: int = 128) -> tuple[bytes, FrameState, dict]:
    """Prepare, never commit. Caller must approve its byte budget first."""
    width = int(bounded_number(width, 320, 1600, 'width'))
    quality = int(bounded_number(quality, 25, 85, 'quality'))
    if image.width * image.height > 64_000_000:
        raise Problem('image_size', '窗口像素过大，请先缩小窗口', 413)
    x, y, w, h = roi
    crop = (int(x * image.width), int(y * image.height),
            max(1, int((x+w) * image.width)), max(1, int((y+h) * image.height)))
    image = image.crop(crop).convert('RGB')
    scale = min(1.0, width / image.width, 1800 / image.height)
    if scale < 1:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    key = (identity, bounds, roi, image.size, quality, tile_size)
    full = previous.key != key or not base or base != previous.revision
    hashes, tiles, bodies = {}, [], []
    for ty in range(0, image.height, tile_size):
        for tx in range(0, image.width, tile_size):
            part = image.crop((tx, ty, min(tx+tile_size, image.width), min(ty+tile_size, image.height)))
            digest = hashlib.blake2s(part.tobytes(), digest_size=16).digest()
            hashes[tx, ty] = digest
            if full or previous.hashes.get((tx, ty)) != digest:
                out = io.BytesIO()
                part.save(out, 'JPEG', quality=quality, optimize=True, subsampling=0)
                raw = out.getvalue()
                tiles.append({'x': tx, 'y': ty, 'w': part.width, 'h': part.height, 'bytes': len(raw)})
                bodies.append(raw)
    revision = secrets.token_hex(12)
    header = {'protocol': 1, 'revision': revision, 'base': base,
              'full': full, 'width': image.width, 'height': image.height,
              'tiles': tiles, 'roi': list(roi), 'image_bytes': sum(map(len, bodies))}
    encoded = compact(header)
    payload = struct.pack('!I', len(encoded)) + encoded + b''.join(bodies)
    candidate = FrameState(revision, key, hashes, bounds, roi, time.monotonic())
    return payload, candidate, header


class ImageBudget:
    """Host-wide cap, cannot be bypassed by refreshing/creating a client.

    Covers encoded frame response bodies, including binary metadata. Does not
    promise a hard cap on TCP/TLS, page assets, semantic or control traffic.
    """
    def __init__(self, limit: int = 5 * 1024 * 1024, per_frame: int = 512 * 1024):
        self.limit, self.per_frame, self.used = limit, per_frame, 0
        self.blocked = 0

    def consume(self, size: int) -> None:
        if size > self.per_frame:
            self.blocked += 1
            raise Problem('frame_too_large', '本次画面超过 512 KiB；请降低清晰度、分辨率或缩小区域', 413)
        if self.used + size > self.limit:
            self.blocked += 1
            raise Problem('budget', '本轮画面预算已用完；画面已暂停，文字仍可用。需在 Mac 重启服务或调整启动参数。', 429)
        self.used += size

    def report(self) -> dict:
        return {'used': self.used, 'limit': self.limit, 'blocked': self.blocked,
                'per_frame': self.per_frame, 'scope': 'host-wide frame response bodies only'}
