"""RAG 检索模块：基于关键词 + 年级匹配的稀疏检索。

设计取舍：使用稀疏（词法）检索而非向量检索，目的是在无 embedding 服务的
情况下也能完全离线运行，且检索结果对用户透明、可追溯——这比"黑盒向量"
更适合面试演示与教学信任。后续如需更强语义匹配，可在 RETRIEVER 处替换为
向量检索实现，对外接口保持不变。
"""

from __future__ import annotations

import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent / "kb"

_GRADE_TOKENS = {"1", "2", "3", "4", "5", "6"}

# 否定语境词：当其紧邻安全关键词出现时，视为"已规避风险"而非"存在风险"。
_NEGATIONS = ["避免", "不用", "禁止", "无", "没有", "不", "未"]


def _load_json(name: str):
    path = KB_DIR / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_curriculum():
    data = _load_json("curriculum.json")
    return data["entries"]


def _load_safety():
    data = _load_json("safety.json")
    return data["rules"]


CURRICULUM = _load_curriculum()
SAFETY_RULES = _load_safety()


def _extract_grades(text: str) -> set[str]:
    return {ch for ch in text if ch in _GRADE_TOKENS}


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    """在课标知识库中检索与查询最相关的片段。

    返回列表，每项包含 id / topic / grades / content / matched_keywords，
    按相关度降序。matched_keywords 用于前端透明展示"为什么检索到这段"。
    """
    grades = _extract_grades(query)
    scored: list[tuple[int, dict]] = []

    for entry in CURRICULUM:
        score = 0
        matched = []
        for kw in entry["keywords"]:
            if kw and kw in query:
                score += 2
                matched.append(kw)
        if entry["topic"] in query:
            score += 3
        if grades and grades & set(entry["grades"]):
            score += 1

        if score > 0:
            scored.append((score, entry, matched))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    return [
        {
            "id": entry["id"],
            "topic": entry["topic"],
            "grades": entry["grades"],
            "content": entry["summary"],
            "misconceptions": entry.get("common_misconceptions", []),
            "matched_keywords": matched,
        }
        for _, entry, matched in top
    ]


def check_safety(text: str) -> list[dict]:
    """根据安全规则库匹配实验文本中的风险点。

    返回命中的规则（按风险等级 high > medium > low 排序），每项含
    level / label / advice，供 Agent 生成安全提示或直接拦截。
    """
    level_rank = {"high": 0, "medium": 1, "low": 2}
    hits: list[tuple[int, dict]] = []

    for rule in SAFETY_RULES:
        matched = False
        for kw in rule["keywords"]:
            if not kw or kw not in text:
                continue
            # 否定语境跳过：如"避免明火""禁止用火"应视为已规避。
            idx = text.index(kw)
            before = text[max(0, idx - 3):idx]
            if any(neg in before for neg in _NEGATIONS):
                continue
            matched = True
            break
        if matched:
            hits.append((level_rank.get(rule["level"], 9), rule))

    hits.sort(key=lambda x: x[0])
    return [
        {
            "level": rule["level"],
            "label": rule["label"],
            "advice": rule["advice"],
        }
        for _, rule in hits
    ]
