"""ScienceCopilot 服务入口。

零依赖（仅标准库）的 HTTP 服务：
- GET  静态资源：/ /index.html /intro.html /styles.css /app.js
- POST /api/inquiry  探究活动生成（Agent + RAG，SSE 流式）
- POST /api/audit    科学内容审核（Agent + RAG，SSE 流式）

接口采用 text/event-stream（SSE）流式返回，并在处理期间发送心跳，
避免云平台的请求超时（免费实例跨洲调用大模型单请求常达数十秒）。
事件类型：
- {"type": "start"}                        请求已接收
- : keepalive                             注释心跳（前端忽略）
- {"type": "done", "trace", "retrieved", "safety", "result", "demo"}  最终结果
- {"type": "error", "error": "..."}       处理异常
"""

import json
import queue
import threading
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

    def _send_event(self, obj) -> None:
        if obj is None:
            # SSE 注释心跳，保持连接活跃，避开平台请求超时
            self.wfile.write(b": keepalive\n\n")
        else:
            data = json.dumps(obj, ensure_ascii=False)
            self.wfile.write(f"event: message\ndata: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

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
            raw = self.rfile.read(length).decode("utf-8") or "{}"
            data = json.loads(raw)
        except Exception:
            data = {}

        if self.path == "/api/inquiry":
            self._handle_agent_sse("inquiry", data)
            return
        if self.path == "/api/audit":
            self._handle_agent_sse("audit", data)
            return
        self._send_json({"error": "Not found"}, status=404)

    def _handle_agent_sse(self, task: str, data: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")  # 禁用 Render/nginx 缓冲
        self.end_headers()

        result_q: "queue.Queue" = queue.Queue()

        def worker() -> None:
            try:
                res = agent.run(task, data)
                result_q.put({"type": "done", **res})
            except Exception as exc:  # noqa: BLE001 - 统一错误出口
                result_q.put({"type": "error", "error": str(exc)})

        threading.Thread(target=worker, daemon=True).start()
        self._send_event({"type": "start"})

        while True:
            try:
                ev = result_q.get(timeout=5)
                self._send_event(ev)
                if ev["type"] in ("done", "error"):
                    break
            except queue.Empty:
                self._send_event(None)  # 心跳保活

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
