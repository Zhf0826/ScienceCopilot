// ScienceCopilot 教师版工作台 — 简洁高效
// 保留全部功能：SSE 流式 / 4 模式 / 结果渲染 / 改一改 / 导出 / 打印 / 历史 / 反馈

const MODES = {
  inquiry: {
    title: "探究活动生成",
    num: "01",
    endpoint: "/api/inquiry",
    btn: "生成探究方案",
    desc: "依据 2022 版课标，为指定年级和主题生成结构化探究活动方案。",
    fields: [
      { id: "grade", label: "年级", type: "text", value: "四年级", placeholder: "例如：四年级" },
      { id: "topic", label: "主题", type: "text", value: "水的蒸发", placeholder: "例如：水的蒸发" },
      { id: "goal", label: "教学目标", type: "textarea", rows: 2, value: "理解蒸发可以在常温下发生，并能设计公平比较实验。" },
      { id: "duration", label: "课堂时间", type: "text", value: "40分钟" },
      { id: "materials", label: "材料限制", type: "text", value: "普通教室材料，避免明火" },
    ],
  },
  audit: {
    title: "科学内容审核",
    num: "02",
    endpoint: "/api/audit",
    btn: "审核科学内容",
    desc: "粘贴教案/讲稿/实验说明，自动核对课标并评估安全。",
    fields: [
      { id: "content", label: "教师文本", type: "textarea", rows: 8, value: "水只有烧开以后才会变成水蒸气，所以蒸发就是沸腾。" },
    ],
  },
  companion: {
    title: "配套与评价资源",
    num: "03",
    endpoint: "/api/companion",
    btn: "生成配套资源",
    desc: "基于主题产出随堂练习、实验报告模板与评分量规。",
    fields: [
      { id: "grade", label: "年级", type: "text", value: "四年级" },
      { id: "topic", label: "主题", type: "text", value: "水的蒸发" },
      { id: "goal", label: "教学目标", type: "textarea", rows: 2, value: "理解蒸发可以在常温下发生。" },
      { id: "plan", label: "探究方案要点（可选）", type: "textarea", rows: 4, value: "" },
    ],
  },
  diagnose: {
    title: "迷思概念诊断",
    num: "04",
    endpoint: "/api/diagnose",
    btn: "生成诊断题",
    desc: "把班级高频错误/学生原话转化为诊断题与教学建议。",
    fields: [
      { id: "grade", label: "年级", type: "text", value: "四年级" },
      { id: "topic", label: "主题", type: "text", value: "水的蒸发" },
      { id: "errors", label: "班级高频错误 / 学生原话", type: "textarea", rows: 4, value: "学生常说：水只有烧开才变成水蒸气；冰消失是太阳吃掉了。" },
    ],
  },
};

const STORAGE_KEY = "sciencecopilot_history_v1";
const FEEDBACK_KEY = "sciencecopilot_feedback_v1";
const lastRun = {};

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

// ---- SSE 流式调用 ----
async function streamAgent(url, payload, handlers) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    handlers.onError && handlers.onError(new Error(text || `HTTP ${response.status}`));
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (raw.startsWith(":")) continue;
      const dataLine = raw.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) continue;
      let evt;
      try {
        evt = JSON.parse(dataLine.slice(6));
      } catch {
        continue;
      }
      if (evt.type === "start") handlers.onStart && handlers.onStart();
      else if (evt.type === "done") handlers.onDone && handlers.onDone(evt);
      else if (evt.type === "error") handlers.onError && handlers.onError(new Error(evt.error));
    }
  }
}

function setLoading(button, message) {
  button.disabled = true;
  button.textContent = message;
}
function clearLoading(button, label) {
  button.disabled = false;
  button.textContent = label;
}

const STEP_LABEL = { thought: "思考", action: "调用工具", observation: "观察", final: "最终答案" };
const LEVEL_LABEL = { high: "高", medium: "中", low: "低" };

// ---- 工具导航 ----
function showTools() {
  document.getElementById("toolsSection").style.display = "block";
  document.getElementById("workWelcome").style.display = "block";
  document.getElementById("workspaceSection").innerHTML = "";
}

function launchTool(modeKey) {
  document.getElementById("toolsSection").style.display = "none";
  document.getElementById("workWelcome").style.display = "none";
  renderWorkspace(modeKey);
}

function renderWorkspace(modeKey) {
  const mode = MODES[modeKey];
  const container = document.getElementById("workspaceSection");
  container.innerHTML = "";

  const header = el("div", "workspace-header");
  header.appendChild(el("h2", null, `${mode.num} ${mode.title}`));
  const backBtn = el("button", "back-link", "← 返回工具列表");
  backBtn.addEventListener("click", showTools);
  header.appendChild(backBtn);
  container.appendChild(header);

  const layout = el("div", "workspace-layout");

  // 左栏：表单
  const formPanel = el("div", "workspace-form");
  formPanel.appendChild(el("h3", null, "输入参数"));
  formPanel.appendChild(el("p", "form-desc", mode.desc));

  mode.fields.forEach((f) => {
    const group = el("div", "form-group");
    const label = el("label", null, f.label);
    group.appendChild(label);
    let input;
    if (f.type === "textarea") {
      input = el("textarea");
      if (f.rows) input.rows = f.rows;
    } else {
      input = el("input");
      input.type = "text";
    }
    input.id = `${modeKey}-${f.id}`;
    input.placeholder = f.placeholder || "";
    input.value = f.value || "";
    group.appendChild(input);
    formPanel.appendChild(group);
  });

  const submitBtn = el("button", "btn-generate form-submit", mode.btn);
  submitBtn.id = `btn-${modeKey}`;
  submitBtn.addEventListener("click", () => doGenerate(modeKey));
  formPanel.appendChild(submitBtn);
  layout.appendChild(formPanel);

  // 右栏：结果
  const resultPanel = el("div", "workspace-result empty");
  resultPanel.id = `result-panel-${modeKey}`;
  resultPanel.innerHTML = '<div class="empty-icon">📋</div><p>填写左侧表单并点击生成，结果将显示在这里。</p>';
  layout.appendChild(resultPanel);

  container.appendChild(layout);
}

// ---- 收集表单数据 ----
function collectData(key) {
  const mode = MODES[key];
  const data = {};
  mode.fields.forEach((f) => {
    const v = document.querySelector(`#${key}-${f.id}`).value.trim();
    if (v) data[f.id] = v;
  });
  return data;
}

// ---- 触发生成 ----
async function doGenerate(key, overrideData) {
  const mode = MODES[key];
  const btn = document.querySelector(`#btn-${key}`);
  const resultPanel = document.querySelector(`#result-panel-${key}`);
  const data = overrideData || collectData(key);

  resultPanel.classList.remove("empty");
  resultPanel.innerHTML = '<pre class="output output-loading">生成中，请稍候（首次调用可能需数十秒）…</pre>';

  setLoading(btn, "Agent 正在规划与检索…");
  try {
    await streamAgent(
      mode.endpoint,
      data,
      {
        onDone: (evt) => {
          lastRun[key] = { data, result: evt.result };
          renderResult(resultPanel, evt, key);
          saveHistory(key, mode, data, evt);
        },
        onError: (e) => {
          resultPanel.innerHTML = `<pre class="output">生成失败：${e.message}</pre>`;
        },
      }
    );
  } finally {
    clearLoading(btn, mode.btn);
  }
}

// ---- 渲染结果 ----
function renderResult(container, data, modeKey) {
  container.innerHTML = "";
  const content = el("div", "result-content");

  // 状态徽标
  const meta = el("div", "meta");
  if (data.demo) {
    meta.appendChild(el("span", "badge badge-demo", "演示模式"));
  }
  if (Array.isArray(data.retrieved) && data.retrieved.length) {
    meta.appendChild(el("span", "badge badge-std", `课标依据 ${data.retrieved.length} 条`));
  }
  if (Array.isArray(data.safety) && data.safety.length) {
    const danger = data.safety.some((s) => s.level === "high");
    meta.appendChild(el("span", danger ? "badge badge-danger" : "badge badge-warn", `安全提示 ${data.safety.length} 项`));
  }
  if (meta.children.length) content.appendChild(meta);

  // 课标卡片
  if (Array.isArray(data.retrieved) && data.retrieved.length) {
    content.appendChild(renderStandardCards(data.retrieved));
  }

  // 安全预案卡
  if (Array.isArray(data.safety) && data.safety.length) {
    content.appendChild(renderSafetyCards(data.safety));
  }

  // 推理轨迹
  if (Array.isArray(data.trace) && data.trace.length) {
    const details = el("details", "trace");
    const summary = el("summary", null, `Agent 推理轨迹（${data.trace.length} 步）`);
    details.appendChild(summary);
    const ol = el("ol");
    data.trace.forEach((step) => {
      const li = el("li", `step step-${step.type}`);
      li.appendChild(el("span", "step-tag", STEP_LABEL[step.type] || step.type));
      const txt = el("span", null, step.type === "action" ? ` ${step.tool}(${JSON.stringify(step.args || {})})` : ` ${step.text || ""}`);
      li.appendChild(txt);
      ol.appendChild(li);
    });
    details.appendChild(ol);
    content.appendChild(details);
  }

  // 检索来源
  if (Array.isArray(data.retrieved) && data.retrieved.length) {
    const details = el("details", "sources");
    details.appendChild(el("summary", null, `知识库来源（${data.retrieved.length} 条）`));
    data.retrieved.forEach((src) => {
      const item = el("div", "source-item");
      item.appendChild(el("div", "source-head",
        `${src.topic} · 适用年级 ${src.grades.join("/")} · 命中：${src.matched_keywords.join("、") || "—"}`));
      const body = el("div", "source-body", src.content);
      item.appendChild(body);
      if (src.core_concept) item.appendChild(el("div", "source-core", `核心概念：${src.core_concept}｜跨学科：${src.crosscutting || "—"}｜素养：${src.competency || "—"}`));
      details.appendChild(item);
    });
    content.appendChild(details);
  }

  // 最终结果
  const pre = el("pre", "output", data.result || "（无结果）");
  content.appendChild(pre);

  // 操作按钮
  content.appendChild(renderActions(content, data, modeKey));

  container.appendChild(content);
}

function renderStandardCards(retrieved) {
  const wrap = el("div", "std-wrap");
  wrap.appendChild(el("div", "block-title", "📘 课标依据"));
  retrieved.forEach((src) => {
    const card = el("div", "std-card");
    card.appendChild(el("div", "std-concept", `核心概念：${src.core_concept || "—"}`));
    card.appendChild(el("div", "std-cross", `跨学科概念：${src.crosscutting || "—"} ｜ 核心素养：${src.competency || "—"}`));
    const ref = src.standard_ref || "（该片段未标注具体引文，依据通用科学常识。）";
    card.appendChild(el("div", "std-ref", ref));
    card.appendChild(el("div", "std-meta", `主题：${src.topic} ｜ 适用年级：${src.grades.join("/")}`));
    wrap.appendChild(card);
  });
  return wrap;
}

function renderSafetyCards(safety) {
  const wrap = el("div", "safety-wrap");
  wrap.appendChild(el("div", "block-title", "🛡️ 安全预案"));
  safety.forEach((s) => {
    const card = el("div", `safety-card safety-${s.level}`);
    const head = el("div", "safety-head");
    head.appendChild(el("span", `safety-badge safety-badge-${s.level}`, `${LEVEL_LABEL[s.level] || s.level}危`));
    head.appendChild(el("span", "safety-label", s.label));
    card.appendChild(head);
    card.appendChild(el("div", "safety-advice", `建议：${s.advice}`));
    if (s.substitute) card.appendChild(el("div", "safety-sub", `替代方案：${s.substitute}`));
    wrap.appendChild(card);
  });
  return wrap;
}

function renderActions(container, data, modeKey) {
  const box = el("div", "result-actions");
  const refineBtn = el("button", "btn-secondary", "✏️ 重新优化");
  const copyBtn = el("button", "btn-secondary", "📋 一键复制");
  const exportBtn = el("button", "btn-secondary", "⬇️ 导出教案");
  const printBtn = el("button", "btn-secondary", "🖨️ 打印");

  refineBtn.addEventListener("click", () => toggleRefine(container, modeKey));
  copyBtn.addEventListener("click", () => copyResult(data));
  exportBtn.addEventListener("click", () => exportMarkdown(modeKey, data));
  printBtn.addEventListener("click", () => printResult(container, modeKey));

  box.appendChild(refineBtn);
  box.appendChild(copyBtn);
  box.appendChild(exportBtn);
  box.appendChild(printBtn);
  return box;
}

function copyResult(data) {
  const text = data.result || "";
  navigator.clipboard.writeText(text).then(() => {
    alert("已复制到剪贴板");
  }).catch(() => {
    // 降级方案
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    alert("已复制到剪贴板");
  });
}

function toggleRefine(container, modeKey) {
  const existing = container.querySelector(".refine-box");
  if (existing) {
    existing.remove();
    return;
  }
  const box = el("div", "refine-box");
  box.appendChild(el("label", "refine-label", "修改意见（在上一版基础上调整，不必重头写）："));
  const ta = el("textarea", "refine-input");
  ta.rows = 3;
  ta.placeholder = "例如：再加一个分组对比实验，步骤写得更具体一些。";
  box.appendChild(ta);
  const row = el("div", "refine-row");
  const apply = el("button", "btn-secondary", "应用修改");
  const cancel = el("button", "btn-secondary ghost", "取消");
  apply.addEventListener("click", () => {
    const prev = lastRun[modeKey];
    if (!prev) return;
    const override = Object.assign({}, prev.data, {
      parent_result: prev.result,
      modify: ta.value.trim(),
    });
    box.remove();
    doGenerate(modeKey, override);
  });
  cancel.addEventListener("click", () => box.remove());
  row.appendChild(apply);
  row.appendChild(cancel);
  box.appendChild(row);
  container.appendChild(box);
}

// ---- 导出 / 打印 ----
function exportMarkdown(modeKey, data) {
  const mode = MODES[modeKey];
  const lines = [`# ScienceCopilot 结果 · ${mode.title}`, "", `> 生成时间：${new Date().toLocaleString("zh-CN")}`, ""];
  if (data.retrieved && data.retrieved.length) {
    lines.push("## 课标依据");
    data.retrieved.forEach((s) => lines.push(`- ${s.standard_ref || s.topic}`));
    lines.push("");
  }
  if (data.safety && data.safety.length) {
    lines.push("## 安全预案");
    data.safety.forEach((s) => {
      lines.push(`- **[${LEVEL_LABEL[s.level] || s.level}危] ${s.label}** ${s.advice}`);
      if (s.substitute) lines.push(`  - 替代方案：${s.substitute}`);
    });
    lines.push("");
  }
  lines.push("## 结果", "", "```text", data.result || "", "```", "");
  lines.push("---", `由 ScienceCopilot AI 生成（${data.demo ? "演示模式" : "真实模型"}）`);

  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sciencecopilot_${modeKey}_${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function printResult(container, modeKey) {
  const mode = MODES[modeKey];
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>ScienceCopilot 打印</title>
  <style>
    body{font-family:"Microsoft YaHei",Arial,sans-serif;color:#1a2b25;padding:32px;line-height:1.7;background:#fff}
    h1{font-size:20px;color:#1a2b25} .std-card,.safety-card{border:1px solid #e2e8e5;border-left:4px solid #16a34a;padding:10px 12px;margin:10px 0;border-radius:6px;background:#f6f8f7}
    .safety-card{border-left-color:#dc2626} .std-ref{background:#f0f4f2;padding:6px 8px;border-radius:4px;margin:6px 0;color:#4a5f57}
    pre{white-space:pre-wrap;background:#f6f8f7;border:1px solid #e2e8e5;border-left:4px solid #d97706;padding:14px;border-radius:8px;color:#4a5f57}
    .foot{color:#7a8f86;margin-top:24px;font-size:12px}
  </style></head><body><h1>ScienceCopilot · ${mode.title}</h1>${container.innerHTML}<div class="foot">由 ScienceCopilot AI 生成（${modeKey}）</div></body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}

// ---- 历史记录 ----
function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}
function saveHistory(modeKey, mode, data, evt) {
  const list = loadHistory();
  list.unshift({
    id: Date.now() + "-" + Math.random().toString(36).slice(2, 7),
    mode: modeKey,
    modeTitle: mode.title,
    time: new Date().toLocaleString("zh-CN"),
    inputs: data,
    payload: { result: evt.result, trace: evt.trace, retrieved: evt.retrieved, safety: evt.safety, demo: evt.demo },
  });
  if (list.length > 50) list.length = 50;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  renderHistory();
}
function renderHistory() {
  const list = loadHistory();
  const box = document.querySelector("#historyList");
  box.innerHTML = "";
  if (!list.length) {
    box.appendChild(el("p", "history-empty", "还没有记录。生成结果后会自动保存在这里。"));
    return;
  }
  list.forEach((item) => {
    const card = el("div", "history-item");
    const head = el("div", "history-item-head");
    head.appendChild(el("span", "history-mode", item.modeTitle));
    head.appendChild(el("span", "history-time", item.time));
    card.appendChild(head);
    const snippet = (item.payload.result || "").replace(/\s+/g, " ").slice(0, 60);
    card.appendChild(el("div", "history-snippet", snippet + (snippet.length >= 60 ? "…" : "")));
    const row = el("div", "history-item-actions");
    const restore = el("button", "ghost-btn", "恢复");
    const del = el("button", "ghost-btn danger", "删除");
    restore.addEventListener("click", () => restoreHistory(item));
    del.addEventListener("click", () => {
      const next = loadHistory().filter((x) => x.id !== item.id);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      renderHistory();
    });
    row.appendChild(restore);
    row.appendChild(del);
    card.appendChild(row);
    box.appendChild(card);
  });
}
function restoreHistory(item) {
  launchTool(item.mode);
  setTimeout(() => {
    MODES[item.mode].fields.forEach((f) => {
      const input = document.querySelector(`#${item.mode}-${f.id}`);
      if (input && item.inputs[f.id] != null) input.value = item.inputs[f.id];
    });
    const resultPanel = document.querySelector(`#result-panel-${item.mode}`);
    if (resultPanel) {
      resultPanel.classList.remove("empty");
      lastRun[item.mode] = { data: item.inputs, result: item.payload.result };
      renderResult(resultPanel, item.payload, item.mode);
    }
  }, 50);
  closeHistory();
}

function openHistory() {
  renderHistory();
  document.querySelector("#historyDrawer").classList.add("is-open");
  document.querySelector("#overlay").classList.add("is-open");
  document.addEventListener("keydown", onHistoryEsc);
}
function closeHistory() {
  document.querySelector("#historyDrawer").classList.remove("is-open");
  document.querySelector("#overlay").classList.remove("is-open");
  document.removeEventListener("keydown", onHistoryEsc);
}
function onHistoryEsc(e) {
  if (e.key === "Escape") closeHistory();
}

// ---- 反馈系统 ----
function initFeedback() {
  const widget = document.getElementById("feedbackWidget");
  const toggle = document.getElementById("feedbackToggle");
  const panel = document.getElementById("feedbackPanel");
  const submit = document.getElementById("feedbackSubmit");
  const cancel = document.getElementById("feedbackCancel");
  const text = document.getElementById("feedbackText");
  let selectedRating = null;

  if (!widget) return;

  toggle.addEventListener("click", () => {
    panel.classList.toggle("is-open");
  });

  panel.querySelectorAll(".feedback-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      panel.querySelectorAll(".feedback-btn").forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedRating = btn.dataset.rating;
    });
  });

  submit.addEventListener("click", () => {
    const feedback = {
      rating: selectedRating,
      text: text.value.trim(),
      time: new Date().toLocaleString("zh-CN"),
      url: window.location.href,
    };
    saveFeedback(feedback);
    panel.classList.remove("is-open");
    text.value = "";
    selectedRating = null;
    panel.querySelectorAll(".feedback-btn").forEach((b) => b.classList.remove("selected"));
    alert("感谢您的反馈！我们会认真阅读并改进。");
  });

  cancel.addEventListener("click", () => {
    panel.classList.remove("is-open");
    text.value = "";
    selectedRating = null;
    panel.querySelectorAll(".feedback-btn").forEach((b) => b.classList.remove("selected"));
  });

  // 点击外部关闭
  document.addEventListener("click", (e) => {
    if (!widget.contains(e.target) && panel.classList.contains("is-open")) {
      panel.classList.remove("is-open");
    }
  });
}

function saveFeedback(feedback) {
  try {
    const list = JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "[]");
    list.unshift(feedback);
    if (list.length > 100) list.length = 100;
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(list));
  } catch {
    // 存储失败静默处理
  }
}

// ---- 从首页快速开始跳转 ----
function applyQuickStart() {
  const grade = sessionStorage.getItem("qs-grade");
  const topic = sessionStorage.getItem("qs-topic");
  const goal = sessionStorage.getItem("qs-goal");
  if (grade || topic || goal) {
    // 自动进入探究活动生成
    launchTool("inquiry");
    setTimeout(() => {
      const gradeInput = document.getElementById("inquiry-grade");
      const topicInput = document.getElementById("inquiry-topic");
      const goalInput = document.getElementById("inquiry-goal");
      if (gradeInput && grade) gradeInput.value = grade;
      if (topicInput && topic) topicInput.value = topic;
      if (goalInput && goal) goalInput.value = goal;
    }, 100);
    // 清除，避免重复应用
    sessionStorage.removeItem("qs-grade");
    sessionStorage.removeItem("qs-topic");
    sessionStorage.removeItem("qs-goal");
  }
}

// ---- 初始化 ----
function init() {
  // 工具卡片点击
  document.querySelectorAll(".tool-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest(".tool-btn")) {
        e.stopPropagation();
        launchTool(card.dataset.mode);
      } else {
        launchTool(card.dataset.mode);
      }
    });
  });

  // 历史记录
  document.querySelector("#openHistory").addEventListener("click", openHistory);
  document.querySelector("#closeHistory").addEventListener("click", closeHistory);
  document.querySelector("#overlay").addEventListener("click", closeHistory);
  document.querySelector("#clearHistory").addEventListener("click", () => {
    if (confirm("确定清空全部历史记录？此操作不可恢复。")) {
      localStorage.removeItem(STORAGE_KEY);
      renderHistory();
    }
  });

  // 引擎状态
  const statusText = document.querySelector("#engineStatus .status-text");
  const statusDot = document.querySelector("#engineStatus .status-dot");
  fetch("/api/status")
    .then((r) => r.json())
    .then((info) => {
      statusText.textContent = info.demo ? "演示模式" : info.model;
      statusDot.classList.toggle("live", !info.demo);
    })
    .catch(() => {
      statusText.textContent = "离线";
    });

  // 反馈系统
  initFeedback();

  // 快速开始跳转
  applyQuickStart();
}

init();
