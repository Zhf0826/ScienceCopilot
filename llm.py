"""LLM 客户端：封装 OpenAI 兼容 Chat Completions 接口。

职责：
- 统一的 chat() 入口，支持普通对话与 function calling（工具调用）。
- DeepSeek 默认关闭思考模式，适合生成/审核这类低延迟场景。
- 无 API Key 时 HAS_KEY 为 False，由上层（agent）切换到确定性演示分支，
  保证页面在没有密钥的环境下也能完整演示交互流程。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config

HAS_KEY = bool(config.API_KEY)


def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.5,
) -> dict:
    """调用模型。

    返回 dict：
    - 普通回复：{"role": "assistant", "content": "..."}
    - 工具调用：{"role": "assistant", "content": None,
                 "tool_calls": [{"name": ..., "arguments": {...}}, ...]}
    """
    if not config.API_KEY:
        raise RuntimeError("未配置 API Key，无法调用真实模型，请使用演示分支。")

    payload: dict = {
        "model": config.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    if "deepseek.com" in (config.OPENAI_BASE_URL or ""):
        payload["thinking"] = {"type": "disabled"}

    request = urllib.request.Request(
        f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except Exception as exc:  # noqa: BLE001 - 向上抛出统一错误
        raise RuntimeError(f"模型接口调用失败：{exc}") from exc

    message = body["choices"][0]["message"]
    tool_calls_raw = message.get("tool_calls")

    if tool_calls_raw:
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", "{}") or "{}"
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append({"name": fn.get("name"), "arguments": arguments})
        return {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": tool_calls,
        }

    return {"role": "assistant", "content": message.get("content") or ""}
