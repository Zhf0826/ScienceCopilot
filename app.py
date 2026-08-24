"""ScienceCopilot 服务入口。

零依赖（仅标准库）的 HTTP 服务：
- GET  静态资源：/ /index.html /intro.html /styles.css /app.js
- POST /api/inquiry  探究活动生成（Agent + RAG）
- POST /api/audit    科学内容审核（Agent + RAG）

返回结构统一为 {"trace", "retrieved", "safety", "result", "demo"}，
便于前端透明展示 Agent 推理轨迹与 RAG 检索来源。
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import agent
import config

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

STATIC_ROUTES = {
    "/": ("text/html; charset=utf-8", "index.html"),
    "/index.html": ("text/html; charset=utf-8", "index.html"),
    "/intro.html": ("text/html; charset=utf-8", "intro.html"),
    "/styles.css": ("text/css; charset=utf-8", "styles.css"),
    "/app.js": ("application/javascript; charset=utf-8", "app.js"),
}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename: str, content_type: str) -> None:
        path = PUBLIC / filename
        if not path.exists():
            self._send_json({"error": "Not found"}, status=404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self._send_json(
                {
                    "demo": not config.API_KEY,
                    "model": config.OPENAI_MODEL if config.API_KEY else None,
                    "base_url": config.OPENAI_BASE_URL,
                }
            )
            return

        route = STATIC_ROUTES.get(self.path)
        if route:
            content_type, filename = route
            self._send_file(filename, content_type)
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")

            if self.path == "/api/inquiry":
                self._send_json(agent.run("inquiry", data))
                return
            if self.path == "/api/audit":
                self._send_json(agent.run("audit", data))
                return

            self._send_json({"error": "Not found"}, status=404)
        except Exception as exc:  # noqa: BLE001 - 统一错误出口
            self._send_json({"error": str(exc)}, status=500)

    # 关闭默认日志噪声，避免刷屏。
    def log_message(self, *args) -> None:  # noqa: D401
        return


def main() -> None:
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    mode = "演示模式(无 API Key)" if not config.API_KEY else f"模型: {config.OPENAI_MODEL}"
    print(f"ScienceCopilot AI 已启动 -> http://{config.HOST}:{config.PORT}  [{mode}]")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
