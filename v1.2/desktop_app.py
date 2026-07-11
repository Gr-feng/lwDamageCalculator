from __future__ import annotations

import argparse
import threading
from http.server import ThreadingHTTPServer
from typing import Optional

import webview

from server import RequestHandler, _ensure_runtime_dirs, _log


APP_TITLE = "东方归言录伤害计算器 v1.2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="lwMAA v1.2 desktop window")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="默认 0 表示自动选择空闲端口")
    parser.add_argument("--debug", action="store_true", help="打开 WebView 调试模式")
    parser.add_argument("--backend-only", action="store_true", help="只启动后端，用于打包后 API 冒烟测试")
    return parser.parse_args()


def start_backend(host: str, port: int) -> tuple[ThreadingHTTPServer, str]:
    _ensure_runtime_dirs()
    httpd = ThreadingHTTPServer((host, port), RequestHandler)
    actual_host, actual_port = httpd.server_address[:2]
    url = f"http://{actual_host}:{actual_port}/"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    _log(f"desktop backend running: {url}")
    return httpd, url


def main() -> None:
    args = parse_args()
    httpd: Optional[ThreadingHTTPServer] = None
    try:
        httpd, url = start_backend(args.host, args.port)
        if args.backend_only:
            _log("backend-only mode")
            httpd.serve_forever()
            return
        window = webview.create_window(
            APP_TITLE,
            url,
            width=1180,
            height=760,
            min_size=(900, 600),
            confirm_close=False,
        )
        _log("desktop window opening")
        webview.start(gui="edgechromium", debug=bool(args.debug))
        _log("desktop window closed")
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    main()
