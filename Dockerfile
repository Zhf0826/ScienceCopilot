# ScienceCopilot 生产镜像 —— 零依赖，仅使用 Python 标准库。
FROM python:3.13-slim

WORKDIR /app

# 仅复制运行所需文件（不复制 .env / .workbuddy / __pycache__）。
COPY app.py config.py llm.py rag.py tools.py agent.py prompts.py ./
COPY kb/ ./kb/
COPY public/ ./public/

# 云平台通过 PORT 环境变量注入端口；HOST 已在 config.py 默认 0.0.0.0。
ENV HOST=0.0.0.0 PORT=8000
EXPOSE 8000

# 启动命令（云平台运行时也会读取容器注入的 PORT）。
CMD ["python", "app.py"]
