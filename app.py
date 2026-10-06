"""
API-ZALO — máy chủ dữ liệu (ảnh/GIF dựng sẵn) cho bot ZALO-BOT.
═══════════════════════════════════════════════════════════════════════
Repo này CHỈ chứa dữ liệu + một máy chủ đọc dữ liệu. Code bot nằm ở repo
khác (ZALO-BOT); bot tải dữ liệu ở đây MỘT LẦN rồi cache trên đĩa.

Vì sao tách ra:
  • repo code nhẹ — clone/pull nhanh, không kéo theo hàng chục MB ảnh;
  • đổi 1 card GIF chỉ cần cập nhật ở đây, bot tự tải bản mới theo sha256;
  • chạy được như một REST API (Render/Railway/VPS) cho nhiều máy dùng
    chung, thay vì mỗi máy phải có sẵn file.

Chạy:
    pip install -r requirements.txt
    python app.py                  # http://0.0.0.0:8080

API:
    GET /                       — danh sách dữ liệu (HTML)
    GET /health                 — {"ok": true, "files": N}
    GET /manifest.json          — sha256 + size của MỌI file
    GET /data/<đường dẫn>       — file thật (ETag + Cache-Control 1 ngày)
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MANIFEST = DATA / "manifest.json"

app = Flask(__name__)


def _load_manifest() -> dict:
    try:
        with open(MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(rel: str) -> Path | None:
    """Chỉ cho phép đường dẫn tương đối nằm trong data/."""
    parts = [p for p in str(rel or "").replace("\\", "/").split("/")
             if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    p = DATA.joinpath(*parts)
    try:
        p.resolve().relative_to(DATA.resolve())
    except Exception:
        return None
    return p


def _mimetype(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".gif": "image/gif",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".json": "application/json; charset=utf-8",
    }.get(ext, "application/octet-stream")


@app.route("/health")
def health():
    man = _load_manifest()
    return jsonify({"ok": True, "files": len(man.get("files") or {}),
                    "generated": man.get("generated")})


@app.route("/manifest.json")
def manifest():
    man = _load_manifest()
    if not man:
        return jsonify({"files": {}, "error": "chưa có manifest"}), 404
    return Response(json.dumps(man, ensure_ascii=False),
                    mimetype="application/json")


@app.route("/data/<path:rel>")
def data_file(rel: str):
    p = _safe(rel)
    if p is None or not p.is_file():
        abort(404)
    try:
        etag = f'"{_sha256(p)[:32]}"'
    except Exception:
        etag = None
    if etag and request.if_none_match and etag in request.if_none_match:
        return Response(status=304)
    resp = send_file(p, mimetype=_mimetype(p), conditional=True)
    # Dữ liệu chỉ đổi khi publish lại ⇒ cache mạnh tay, có ETag để xác thực.
    resp.headers["Cache-Control"] = "public, max-age=86400"
    if etag:
        resp.headers["ETag"] = etag
    return resp


@app.route("/")
def index():
    man = _load_manifest()
    files = man.get("files") or {}
    total = sum(int(v.get("size") or 0) for v in files.values()
                if isinstance(v, dict))
    rows = "".join(
        f'<li><a href="/data/{k}">{k}</a> — '
        f'{int((files[k] or {}).get("size") or 0) // 1024} KB</li>'
        for k in sorted(files)
    )
    return (
        "<h1>API-ZALO — kho dữ liệu bot</h1>"
        f"<p>{len(files)} file · {total // 1024} KB · "
        f"manifest: {man.get('generated') or 'chưa có'}</p>"
        f"<ul>{rows}</ul>"
        "<p>Cập nhật bằng: <code>python tools/publish_api_data.py "
        "--publish --push</code> (chạy trong repo ZALO-BOT).</p>"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or 8080)
    app.run(host="0.0.0.0", port=port, threaded=True)
