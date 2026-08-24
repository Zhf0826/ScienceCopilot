"""Agent 编排器：ReAct 风格的工具调用循环。

两条执行分支：
- 有 API Key：真实 function calling，模型自主决定调用哪些工具，循环最多
  AGENT_MAX_ITERATIONS 次后产出最终答案。
- 无 API Key：确定性演示分支，但 retrieve_curriculum / check_safety 仍是真实
  调用（RAG 与安全检查不依赖模型），仅"最终作答"用模板合成，保证离线也能
  完整演示 Agent + RAG 流程。

对外统一返回 {"trace", "retrieved", "safety", "result", "demo"}，
前端据此透明展示"推理轨迹 + 检索来源 + 安全提示 + 最终方案"。
"""

from __future__ import annotations

import json

import config
import llm
import rag
import tools
from prompts import (
    AUDIT_SYSTEM,
    INQUIRY_SYSTEM,
    build_audit_user_prompt,
    build_inquiry_user_prompt,
)


def run(task: str, data: dict) -> dict:
    if task == "inquiry":
        system = INQUIRY_SYSTEM
        user = build_inquiry_user_prompt(data)
        query = f"{data.get('grade','')} {data.get('topic','')} {data.get('goal','')}"
        text = f"{data.get('materials','')} {data.get('goal','')}"
    elif task == "audit":
        system = AUDIT_SYSTEM
        user = build_audit_user_prompt(data)
        query = data.get("content", "")
        text = data.get("content", "")
    else:
        raise ValueError(f"未知任务类型：{task}")

    if llm.HAS_KEY:
        return _run_real(system, user, query, text)
    return _run_demo(task, data, query, text)


def _run_real(system: str, user: str, query: str, text: str) -> dict:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    trace: list[dict] = []
    retrieved = rag.retrieve(query)
    safety = rag.check_safety(text)

    for _ in range(config.AGENT_MAX_ITERATIONS):
        resp = llm.chat(messages, tools=tools.TOOL_SCHEMAS)

        if resp.get("tool_calls"):
            if resp.get("content"):
                trace.append({"type": "thought", "text": resp["content"]})
            messages.append(
                {
                    "role": "assistant",
                    "content": resp.get("content"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(
                                    tc["arguments"], ensure_ascii=False
                                ),
                            },
                        }
                        for tc in resp["tool_calls"]
                    ],
                }
            )
            for tc in resp["tool_calls"]:
                obs = tools.execute(tc["name"], tc["arguments"])
                trace.append(
                    {"type": "action", "tool": tc["name"], "args": tc["arguments"]}
                )
                trace.append({"type": "observation", "text": obs})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tc["name"],
                        "content": obs,
                    }
                )
            continue

        result = resp["content"]
        trace.append({"type": "final", "text": result})
        return {
            "trace": trace,
            "retrieved": retrieved,
            "safety": safety,
            "result": result,
            "demo": False,
        }

    return {
        "trace": trace,
        "retrieved": retrieved,
        "safety": safety,
        "result": "（模型在限定步数内未给出最终答案，请重试或简化需求。）",
        "demo": False,
    }


def _run_demo(task: str, data: dict, query: str, text: str) -> dict:
    retrieved = rag.retrieve(query)
    safety = rag.check_safety(text)
    trace: list[dict] = []

    trace.append(
        {"type": "thought", "text": "规划：先检索课标核心概念，再评估实验安全，最后综合作答。"}
    )

    retrieve_args = {
        "topic": data.get("topic", ""),
        "grade": data.get("grade", ""),
        "goal": data.get("goal", ""),
    }
    obs = tools.execute("retrieve_curriculum", retrieve_args)
    trace.append({"type": "action", "tool": "retrieve_curriculum", "args": retrieve_args})
    trace.append({"type": "observation", "text": obs})

    safety_args = {"materials": data.get("materials", ""), "plan_text": text}
    safety_obs = tools.execute("check_safety", safety_args)
    trace.append({"type": "action", "tool": "check_safety", "args": safety_args})
    trace.append({"type": "observation", "text": safety_obs})

    trace.append({"type": "thought", "text": "综合检索证据与安全评估，生成最终答案。"})

    if task == "inquiry":
        result = _demo_inquiry(data, retrieved, safety)
    else:
        result = _demo_audit(data, retrieved, safety)

    trace.append({"type": "final", "text": result})
    return {
        "trace": trace,
        "retrieved": retrieved,
        "safety": safety,
        "result": result,
        "demo": True,
    }


def _demo_inquiry(data: dict, retrieved: list[dict], safety: list[dict]) -> str:
    topic = data.get("topic", "本主题").strip() or "本主题"
    grade = data.get("grade", "").strip() or "对应年级"
    goal = data.get("goal", "").strip() or "理解核心科学概念"
    duration = data.get("duration", "").strip() or "一节课"
    materials = data.get("materials", "").strip() or "普通教室材料"

    top = retrieved[0] if retrieved else None
    misconceptions = "；".join(top["misconceptions"]) if top else "根据内容引导学生反思直觉。"
    explanation = top["content"] if top else "请结合课标核心概念进行解释。"

    safety_note = ""
    if safety:
        level_label = {"high": "高", "medium": "中", "low": "低"}
        joined = "；".join(f"[{level_label.get(s['level'])}危]{s['label']}：{s['advice']}" for s in safety)
        safety_note = f"\n\n【安全提示】\n{joined}"

    return f"""【探究主题】
{topic}

【核心问题】
关于"{topic}"，学生在{grade}阶段最可能感到困惑的问题是什么？我们能通过怎样的公平比较来寻找答案？

【实验/探究活动】
围绕"{topic}"设计一个可在普通教室完成的对比/观察类探究，让学生在{duration}内经历"提问—预测—验证—解释"的完整过程。

【材料】
{materials}。

【步骤】
1. 明确要比较的变量，保证其他条件相同（公平实验）。
2. 分组进行观察或测量，记录初始状态。
3. 按时间或条件变化重复观察，收集证据。
4. 汇总数据，讨论现象背后的原因。

【观察记录】
记录时间/条件、观察到的现象、学生的推测与疑问。

【教师引导问题】
你怎样保证比较是公平的？除了已经想到的因素，还有哪些可能影响结果？

【学生可能错误概念】
{misconceptions}

【科学解释】
{explanation}{safety_note}

提示：当前未配置 API Key，以上为基于课标知识库与安全检查的本地演示结果；配置密钥后将由模型生成更贴合你输入的方案。"""


def _demo_audit(data: dict, retrieved: list[dict], safety: list[dict]) -> str:
    content = data.get("content", "").strip()
    top = retrieved[0] if retrieved else None

    # 演示启发式：检测"只有烧开才会蒸发"这类常见误区。
    if ("烧开" in content or "沸腾" in content) and ("蒸发" in content or "水蒸气" in content):
        return f"""【审核结果】
需要修改。

【发现的问题】
文本可能把"蒸发"和"沸腾"混为一谈，容易让学生误以为水只有烧开才会变成水蒸气。

【错误等级】
中

【科学原因】
蒸发在常温下也能发生（液体表面缓慢汽化），沸腾是在达到沸点时液体内部和表面同时剧烈汽化，二者条件与剧烈程度不同。

【修改建议】
将"水只有烧开以后才会变成水蒸气，所以蒸发就是沸腾"改为"水在常温下也会慢慢蒸发，温度升高通常会让蒸发更快"。

【推荐表达】
我们看不见水蒸气，但可以通过水量减少、衣服变干等现象发现水正在蒸发。

提示：当前未配置 API Key，以上为本地演示审核结果。"""

    if any(s["level"] == "high" for s in safety):
        joined = "；".join(s["advice"] for s in safety if s["level"] == "high")
        return f"""【审核结果】
需要修改（安全）。

【发现的问题】
文本/方案涉及高风险操作，未给出充分安全说明。

【错误等级】
高

【科学原因】
小学阶段应优先使用安全的观察型活动，避免明火、市电、强化学品等风险源。

【修改建议】
移除或替换高风险步骤，改用低压电池、生活安全材料，并补充教师看护说明。

【推荐表达】
{joined}

提示：当前未配置 API Key，以上为本地演示审核结果。"""

    concept = top["content"] if top else "请对照课标核心概念确认表述准确性。"
    return f"""【审核结果】
基本正确，建议微调。

【发现的问题】
表述整体无误，个别措辞可更贴近小学生认知。

【错误等级】
低

【科学原因】
{concept}

【修改建议】
用学生能感知的现象（如观察、比较）替代抽象术语，并预留探究空间。

【推荐表达】
引导学生先预测再验证，而不是直接给出结论。

提示：当前未配置 API Key，以上为本地演示审核结果。"""
