"""工具层：Agent 在 ReAct 循环中可调用的函数及其 schema。

目前提供两个核心工具，正好对应"知识库 RAG"与"实验安全"两个关键能力：
- retrieve_curriculum：从课标知识库检索相关核心概念与常见误区。
- check_safety：根据安全规则库检查实验材料/步骤中的风险点。

新增工具时，只需在 TOOL_REGISTRY 注册函数并在 TOOL_SCHEMAS 补充 schema，
agent 即可自动发现并调用，无需改动编排逻辑。
"""

from __future__ import annotations

import rag

TOOL_REGISTRY: dict[str, callable] = {}


def register(name: str):
    def deco(fn: callable) -> callable:
        TOOL_REGISTRY[name] = fn
        return fn

    return deco


@register("retrieve_curriculum")
def retrieve_curriculum(grade: str = "", topic: str = "", goal: str = "") -> str:
    """从小学科学课标知识库检索与年级/主题相关的核心概念、常见误区。"""
    query = f"{grade} {topic} {goal}"
    hits = rag.retrieve(query, top_k=4)
    if not hits:
        return "（课标库未检索到高度相关片段，请基于通用科学常识谨慎生成。）"

    lines = ["【检索到的课标参考】"]
    for i, h in enumerate(hits, 1):
        lines.append(
            f"({i}) 主题：{h['topic']}（适用年级：{', '.join(h['grades'])}；"
            f"匹配关键词：{', '.join(h['matched_keywords'])}）"
        )
        lines.append(f"    概念：{h['content']}")
        if h["misconceptions"]:
            lines.append("    常见误区：" + "；".join(h["misconceptions"]))
    return "\n".join(lines)


@register("check_safety")
def check_safety(materials: str = "", plan_text: str = "") -> str:
    """检查实验材料与步骤中的安全风险，返回命中规则与处置建议。"""
    text = f"{materials} {plan_text}"
    hits = rag.check_safety(text)
    if not hits:
        return "（安全规则库未检出明显风险，仍建议教师现场评估。）"

    level_label = {"high": "高", "medium": "中", "low": "低"}
    lines = ["【实验安全检查结果】"]
    for h in hits:
        lines.append(f"[{level_label.get(h['level'], h['level'])}危] {h['label']}")
        lines.append(f"    建议：{h['advice']}")
        if h.get("substitute"):
            lines.append(f"    替代方案：{h['substitute']}")
    return "\n".join(lines)


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_curriculum",
            "description": "从小学科学课标知识库检索与年级/主题相关的核心概念、常见误区。"
            "生成或审核探究方案前应先调用，以保证内容符合课标。",
            "parameters": {
                "type": "object",
                "properties": {
                    "grade": {"type": "string", "description": "年级，如 四年级"},
                    "topic": {"type": "string", "description": "教学主题，如 水的蒸发"},
                    "goal": {"type": "string", "description": "教学目标或待审核文本片段"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_safety",
            "description": "检查实验材料与步骤中的安全风险（明火、用电、化学品、锐器等），"
            "返回风险等级与处置建议。设计涉及动手操作的方案时应调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "materials": {"type": "string", "description": "拟使用的材料列表"},
                    "plan_text": {"type": "string", "description": "实验步骤或方案文本"},
                },
                "required": [],
            },
        },
    },
]


def execute(name: str, arguments: dict) -> str:
    """执行指定工具，返回观察结果字符串。"""
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"（未知工具：{name}）"
    try:
        return fn(**arguments)
    except TypeError:
        return f"（工具 {name} 参数错误：{arguments}）"
