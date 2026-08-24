"""ScienceCopilot 运行配置。

所有可调项都从环境变量读取，便于在不同环境（本地 / 面试演示 / 云端）切换。
优先使用 DEEPSEEK_API_KEY，未设置时回退到 OPENAI_API_KEY。
"""

import os

# 默认 0.0.0.0：允许云平台/容器的外部访问。本地调试可临时设 HOST=127.0.0.1 仅本机监听。
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
IS_DEEPSEEK = bool(os.environ.get("DEEPSEEK_API_KEY"))

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

if not OPENAI_BASE_URL:
    OPENAI_BASE_URL = (
        "https://api.deepseek.com" if IS_DEEPSEEK else "https://api.openai.com/v1"
    )

if not OPENAI_MODEL:
    OPENAI_MODEL = "deepseek-chat" if IS_DEEPSEEK else "gpt-4.1-mini"

# Agent 最多循环调用工具的次数，防止模型陷入无限工具循环。
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "6"))

# RAG 检索返回的课标片段数量。
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))
