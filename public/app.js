// 以 SSE 流式调用 Agent 接口，边生成边接收事件，避免云平台长请求超时。
async function streamAgent(url, payload, handlers) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    handlers.onError(new Error(text || `HTTP ${response.status}`));
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
      if (raw.startsWith(":")) continue; // SSE 心跳注释，忽略
      const dataLine = raw
        .split("\n")
        .find((line) => line.startsWith("data: "));
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

const STEP_LABEL = {
  thought: "思考",
  action: "调用工具",
  observation: "观察",
  final: "最终答案",
};

function renderResult(container, data) {
  container.innerHTML = "";

  // 状态徽标行
  const meta = document.createElement("div");
  meta.className = "meta";
  if (data.demo) {
    const b = document.createElement("span");
    b.className = "badge badge-demo";
    b.textContent = "演示模式（无 API Key，RAG/安全为真实检索）";
    meta.appendChild(b);
  }
  if (Array.isArray(data.safety) && data.safety.length) {
    const danger = data.safety.some((s) => s.level === "high");
    const b = document.createElement("span");
    b.className = danger ? "badge badge-danger" : "badge badge-warn";
    b.textContent = `安全提示：${data.safety.length} 项`;
    meta.appendChild(b);
  }
  if (meta.children.length) container.appendChild(meta);

  // 推理轨迹
  if (Array.isArray(data.trace) && data.trace.length) {
    const details = document.createElement("details");
    details.className = "trace";
    const summary = document.createElement("summary");
    summary.textContent = `Agent 推理轨迹（${data.trace.length} 步）`;
    details.appendChild(summary);

    const ol = document.createElement("ol");
    for (const step of data.trace) {
      const li = document.createElement("li");
      li.className = `step step-${step.type}`;
      const tag = document.createElement("span");
      tag.className = "step-tag";
      tag.textContent = STEP_LABEL[step.type] || step.type;
      li.appendChild(tag);

      if (step.type === "action") {
        const txt = document.createElement("span");
        txt.textContent = ` ${step.tool}(${JSON.stringify(step.args || {})})`;
        li.appendChild(txt);
      } else {
        const txt = document.createElement("span");
        txt.textContent = ` ${step.text || ""}`;
        li.appendChild(txt);
      }
      ol.appendChild(li);
    }
    details.appendChild(ol);
    container.appendChild(details);
  }

  // 检索来源
  if (Array.isArray(data.retrieved) && data.retrieved.length) {
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `RAG 检索来源（${data.retrieved.length} 条）`;
    details.appendChild(summary);

    for (const src of data.retrieved) {
      const item = document.createElement("div");
      item.className = "source-item";
      const head = document.createElement("div");
      head.className = "source-head";
      head.textContent = `${src.topic} · 适用年级 ${src.grades.join(
        "/"
      )} · 命中关键词：${src.matched_keywords.join("、") || "—"}`;
      const body = document.createElement("div");
      body.className = "source-body";
      body.textContent = src.content;
      item.appendChild(head);
      item.appendChild(body);
      details.appendChild(item);
    }
    container.appendChild(details);
  }

  // 最终结果
  const pre = document.createElement("pre");
  pre.className = "output";
  pre.textContent = data.result || "（无结果）";
  container.appendChild(pre);
}

const generateBtn = document.querySelector("#generateBtn");
const auditBtn = document.querySelector("#auditBtn");
const inquiryResult = document.querySelector("#inquiryResult");
const auditResult = document.querySelector("#auditResult");

generateBtn.addEventListener("click", async () => {
  setLoading(generateBtn, "Agent 正在规划与检索…");
  inquiryResult.innerHTML =
    '<pre class="output output-loading">生成中，请稍候（首次调用可能需数十秒）…</pre>';
  try {
    await streamAgent(
      "/api/inquiry",
      {
        grade: document.querySelector("#grade").value,
        topic: document.querySelector("#topic").value,
        goal: document.querySelector("#goal").value,
        duration: document.querySelector("#duration").value,
        materials: document.querySelector("#materials").value,
      },
      {
        onDone: (data) => renderResult(inquiryResult, data),
        onError: (e) => {
          inquiryResult.innerHTML = `<pre class="output">生成失败：${e.message}</pre>`;
        },
      }
    );
  } finally {
    clearLoading(generateBtn, "生成探究方案");
  }
});

auditBtn.addEventListener("click", async () => {
  setLoading(auditBtn, "Agent 正在检索与审核…");
  auditResult.innerHTML =
    '<pre class="output output-loading">生成中，请稍候（首次调用可能需数十秒）…</pre>';
  try {
    await streamAgent(
      "/api/audit",
      {
        content: document.querySelector("#auditText").value,
      },
      {
        onDone: (data) => renderResult(auditResult, data),
        onError: (e) => {
          auditResult.innerHTML = `<pre class="output">审核失败：${e.message}</pre>`;
        },
      }
    );
  } finally {
    clearLoading(auditBtn, "审核科学内容");
  }
});

// 启动时探测引擎状态（演示模式 / 真实模型）
(async () => {
  const status = document.querySelector("#engineStatus");
  try {
    const res = await fetch("/api/status");
    const info = await res.json();
    status.textContent = info.demo
      ? "演示模式 · 离线可用"
      : `模型 ${info.model}`;
    status.classList.add(info.demo ? "status-demo" : "status-live");
  } catch {
    status.textContent = "状态未知";
  }
})();
