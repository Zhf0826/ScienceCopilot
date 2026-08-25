# ScienceCopilot AI

> 小学科学教师智能助手 · 由 **LLM + Prompt Engineering + Agent 工作流 + 知识库 RAG** 驱动。

ScienceCopilot 帮助小学 3-6 年级科学教师完成两件高频工作：**生成探究活动方案** 与
**审核科学教学内容**。它不是一个单纯的"AI 补全框"，而是一个会规划、会查课标、
能评估实验安全的 Agent：先用工具获取证据（RAG 检索 + 安全检查），再产出结构化结果。

---

## 功能

四大工具，覆盖教师「备课 → 上课 → 评价 → 复盘」链路中的高频痛点：

| 功能 | 输入 | 输出 |
| --- | --- | --- |
| 01 探究活动生成 | 年级 / 主题 / 教学目标 / 课堂时间 / 材料限制 | 10 个固定栏目的探究方案 |
| 02 科学内容审核 | 一段教学文本 | 6 个固定栏目的审核结论（含错误等级与修改建议） |
| 03 配套与评价资源 | 年级 / 主题 / 教学目标 / 方案要点 | 随堂练习 + 实验报告模板 + 评分量规 |
| 04 迷思概念诊断 | 年级 / 主题 / 班级高频错误 / 学生原话 | 诊断题 + 解析 + 教学建议 |

四个功能都经过 Agent 编排：自动检索课标概念、自动评估实验安全，并在前端透明展示
**推理轨迹**、**RAG 检索来源** 与 **安全提示**。

### 面向教师的增强能力（差异化壁垒）

- **📘 课标依据卡片**：结果页把 RAG 检索到的《义务教育科学课程标准（2022年版）》核心概念、
  跨学科概念、核心素养与具体引文直接渲染成卡片——通用 AI 给不出可标注的课标出处。
- **🛡️ 安全预案**：`check_safety` 命中风险后，不只红色告警，还给出**可落地的替代方案**
  （如"市电 → 改用 1.5V/3V 低压电池盒"），教师真正敢用。
- **✏️ 改一改**：每个结果下方可写修改意见，在上一版基础上定向迭代，而非从零重写。
- **⬇️ 导出 / 🖨️ 打印**：结果一键导出 Markdown 或浏览器打印，便于带去教室、交教研。
- **🕘 历史记录**：每次结果自动存入本机浏览器（localStorage），可恢复、删除、清空，
  形成个人教案资产。

---

 AI 架构（四层）

1. LLM** — OpenAI 兼容接口（默认 DeepSeek / 可切 OpenAI），负责生成与推理。
2. **Prompt Engineering** — 角色 + 约束 + 固定【栏目】输出格式，结果可解析、可评测。
3. **Agent 工作流** — ReAct 风格循环：规划 → 调用工具 → 观察 → 反思 → 产出。
4. **知识库 RAG** — 检索课标核心概念与常见误区，让生成"有据可依"。

```
用户需求
  │
  ▼
Agent 编排器 (Planner + ReAct 循环)
  │  ├─ retrieve_curriculum  ──►  RAG 课标库 (kb/curriculum.json)
  │  └─ check_safety         ──►  安全规则库 (kb/safety.json)
  ▼
结构化结果 (trace + retrieved + safety + result)
```

> 演示模式（无 API Key）下，Agent 走确定性分支，但 RAG 检索与安全检查仍是真实调用，
> 仅"最终作答"用模板合成，保证离线也能完整演示 Agent + RAG 流程。

---

运行

 方式一：直接运行（演示模式，离线可用）

```powershell
python app.py
```

打开 http://127.0.0.1:8000 。无需任何 API Key，页面可完整演示交互与检索过程。

 方式二：接入 DeepSeek（真实模型 + 工具调用）

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python app.py
```

默认会使用：

```text
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

DeepSeek 请求默认关闭思考模式，适合快速生成与审核场景。

 方式三：使用 OpenAI

```powershell
$env:OPENAI_API_KEY="你的 OpenAI API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
python app.py
```

 可选配置

```powershell
$env:OPENAI_MODEL="deepseek-chat"      # 模型名
$env:OPENAI_BASE_URL="https://..."     # 兼容 OpenAI 的接口地址
$env:PORT="8000"                       # 端口
$env:AGENT_MAX_ITERATIONS="6"          # Agent 最大工具循环次数
$env:RAG_TOP_K="4"                     # RAG 返回片段数
```

---

 项目结构

```text
ScienceCopilot
├── app.py                 # 服务入口：路由 + 静态资源 + 两个 API
├── config.py              # 环境变量配置
├── llm.py                 # LLM 客户端（function calling + 无 Key 兜底）
├── rag.py                 # 知识库加载与稀疏检索 + 安全检查
├── tools.py               # Agent 可调用工具及 OpenAI tool schema
├── agent.py               # Agent 编排器（ReAct 循环 + 真实/演示双分支）
├── prompts.py             # 系统提示与输出格式规范
├── kb/
│   ├── curriculum.json    # 课标核心概念库
│   └── safety.json        # 实验安全规则库
├── public/
│   ├── index.html         # 主应用
│   ├── intro.html         # 项目介绍页
│   ├── styles.css
│   └── app.js
├── tests/                 # 单元测试（stdlib unittest）
└── README.md
```

---

 API

所有接口返回统一结构：

```json
{
  "trace":   [ {"type": "thought|action|observation|final", "text"|"tool"|"args": ...} ],
  "retrieved": [ {"id","topic","grades","content","misconceptions","matched_keywords"} ],
  "safety":  [ {"level":"high|medium|low","label","advice"} ],
  "result":  "【栏目】... 最终文本",
  "demo":    false
}
```

- `POST /api/inquiry` — 探究活动生成，body：`{grade, topic, goal, duration, materials}`
- `POST /api/audit` — 科学内容审核，body：`{content}`
- `POST /api/companion` — 配套与评价资源，body：`{grade, topic, goal, plan}`
- `POST /api/diagnose` — 迷思概念诊断，body：`{grade, topic, errors}`
- `GET  /api/status` — 引擎状态：`{demo, model, base_url}`

> 所有生成类接口都支持 `parent_result` + `modify` 两个可选字段，用于「改一改」迭代：
> 传入上一版结果与修改意见，模型在保留优点的前提下定向优化。

---

测试

```powershell
python -m unittest discover -s tests
```

覆盖 RAG 检索、安全检查、工具执行与 Agent 演示分支。

--

---

## 路线图

MVP 加固 → 单 Agent（规划 + 工具 + 反思）→ 多 Agent 协作（设计 / 审核 / 安全）
+ 向量 RAG + 记忆层 → 评测集与 Trace 面板 + 一键部署。
