const POLL_MS = 3000;
const COMPLETED_PHASES = new Set([
  "passed_waiting_human_merge",
  "stopped_no_action",
  "stopped_budget",
  "stopped_blocked",
]);

const PHASE_LABELS = {
  passed_waiting_human_merge: "通过，等待人工合并",
  stopped_no_action: "停止：无需操作",
  stopped_budget: "停止：预算耗尽",
  stopped_blocked: "停止：阻塞",
  repair_needed: "需要修复",
  invalid_artifact: "产物无效",
};

const HEALTH_LABELS = {
  progressing: "运行中",
  completed: "完成",
  blocked: "阻塞",
};

const STATUS_LABELS = {
  done: "完成",
  running: "运行中",
  waiting: "等待",
  blocked: "阻塞",
};

const AGENT_LABELS = {
  planner: "Planner",
  generator: "Generator",
  evaluator: "Evaluator",
};

const state = {
  project: null,
  runs: [],
  selectedRunId: "",
  detail: null,
  events: [],
  logs: [],
  loadingDetailFor: "",
  lastError: "",
  pollTimer: 0,
};

const els = {
  pollState: document.getElementById("poll-state"),
  projectStatus: document.getElementById("project-status-content"),
  runList: document.getElementById("run-list"),
  completedRuns: document.getElementById("completed-runs"),
  runDetail: document.getElementById("run-detail-content"),
  flowDiagram: document.getElementById("flow-diagram"),
  agentCards: document.getElementById("agent-cards"),
  diagnostics: document.getElementById("blocked-diagnostics"),
  kindFilter: document.getElementById("log-kind-filter"),
  keywordFilter: document.getElementById("log-keyword-filter"),
  logList: document.getElementById("log-list"),
};

function text(value, fallback = "暂无") {
  const normalized = value === null || value === undefined ? "" : String(value);
  return normalized.trim() || fallback;
}

function phaseLabel(phase) {
  return PHASE_LABELS[phase] || text(phase);
}

function healthLabel(health) {
  return HEALTH_LABELS[health] || text(health);
}

function statusLabel(status) {
  return STATUS_LABELS[status] || text(status);
}

function setChildren(parent, children) {
  parent.replaceChildren(...children);
}

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (content !== undefined && content !== null) {
    node.textContent = String(content);
  }
  return node;
}

function empty(message) {
  return el("div", "empty", message);
}

function errorNode(message) {
  return el("div", "error-message", message);
}

async function fetchJson(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_error) {
      detail = response.statusText;
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function refresh() {
  try {
    const [project, runs] = await Promise.all([fetchJson("/api/projects/current"), fetchJson("/api/runs")]);
    state.project = project;
    state.runs = Array.isArray(runs) ? runs : [];
    state.lastError = "";
    let recoverableNotice = "";
    renderProject();

    if (state.runs.length === 0) {
      state.selectedRunId = "";
      state.detail = null;
      state.events = [];
      state.logs = [];
      renderAll();
      setPollState("无运行记录");
      return;
    }

    const selectedStillExists = state.runs.some((run) => run.run_id === state.selectedRunId);
    if (!selectedStillExists) {
      const disappeared = Boolean(state.selectedRunId);
      state.selectedRunId = state.runs[0].run_id;
      if (disappeared) {
        recoverableNotice = "原选中运行已不存在，已切换到最新运行。";
      }
    }

    renderRunLists();
    if (state.selectedRunId && state.loadingDetailFor !== state.selectedRunId) {
      await selectRun(state.selectedRunId, { silent: true });
      if (recoverableNotice) {
        state.lastError = recoverableNotice;
        renderAll();
      }
    } else {
      state.lastError = recoverableNotice;
      renderAll();
    }
    setPollState(`已同步 ${formatTime(new Date().toISOString())}`);
  } catch (error) {
    state.lastError = `读取失败：${error.message}`;
    setPollState("同步失败");
    renderErrorState();
  }
}

async function selectRun(runId, options = {}) {
  if (!runId) {
    return;
  }
  state.selectedRunId = runId;
  state.loadingDetailFor = runId;
  if (!options.silent) {
    renderRunLists();
    setChildren(els.runDetail, [empty("正在读取运行详情...")]);
  }

  try {
    const [detail, eventsResponse, logsResponse] = await Promise.all([
      fetchJson(`/api/runs/${encodeURIComponent(runId)}`),
      fetchJson(`/api/runs/${encodeURIComponent(runId)}/events`),
      fetchJson(`/api/runs/${encodeURIComponent(runId)}/logs`),
    ]);
    if (state.selectedRunId !== runId) {
      return;
    }
    state.detail = detail;
    state.events = Array.isArray(eventsResponse.events) ? eventsResponse.events : [];
    state.logs = Array.isArray(logsResponse.logs) ? logsResponse.logs : [];
    state.lastError = "";
    renderAll();
  } catch (error) {
    if (error.status === 404) {
      state.lastError = `选中的运行已消失：${runId}`;
      state.detail = null;
      state.events = [];
      state.logs = [];
      const fallback = state.runs.find((run) => run.run_id !== runId);
      if (fallback) {
        state.selectedRunId = fallback.run_id;
      }
    } else {
      state.lastError = `读取运行失败：${error.message}`;
    }
    renderAll();
  } finally {
    state.loadingDetailFor = "";
  }
}

function renderAll() {
  renderProject();
  renderRunLists();
  renderDetail();
  renderFlow();
  renderAgents();
  renderDiagnostics();
  renderLogs();
}

function renderProject() {
  if (!state.project) {
    setChildren(els.projectStatus, [empty("正在读取项目状态...")]);
    return;
  }
  const rows = [
    ["项目根", state.project.project_root],
    ["运行目录", state.project.loop_runs_path],
    ["目录状态", state.project.loop_runs_exists ? "已发现" : "未创建"],
  ].map(([key, value]) => {
    const dl = el("dl", "kv");
    dl.append(el("dt", "", key), el("dd", "", text(value)));
    return dl;
  });
  setChildren(els.projectStatus, rows);
}

function renderRunLists() {
  if (state.runs.length === 0) {
    setChildren(els.runList, [empty("暂无运行记录。等待 .codex/loop-runs 生成后会自动刷新。")]);
    setChildren(els.completedRuns, [empty("暂无已完成运行")]);
    return;
  }

  setChildren(els.runList, state.runs.map((run) => runButton(run, "run-button")));

  const completed = state.runs.filter((run) => run.completed || COMPLETED_PHASES.has(run.phase));
  if (completed.length === 0) {
    setChildren(els.completedRuns, [empty("暂无已完成运行")]);
    return;
  }
  setChildren(els.completedRuns, completed.map((run) => runButton(run, "completed-button")));
}

function runButton(run, className) {
  const button = el("button", `${className}${run.run_id === state.selectedRunId ? " is-selected" : ""}`);
  button.type = "button";
  button.dataset.runId = run.run_id;
  button.setAttribute("aria-pressed", run.run_id === state.selectedRunId ? "true" : "false");
  button.addEventListener("click", () => selectRun(run.run_id));

  const topline = el("div", className === "run-button" ? "run-topline" : "completed-topline");
  topline.append(el("span", className === "run-button" ? "run-id" : "completed-id", text(run.run_id)));
  topline.append(el("span", `badge health-${text(run.health, "progressing")}`, healthLabel(run.health)));

  button.append(
    topline,
    el("div", className === "run-button" ? "run-summary" : "completed-summary", text(run.task_summary)),
    el("div", className === "run-button" ? "run-meta" : "completed-meta", `${phaseLabel(run.phase)} · ${formatTime(run.updated_at)}`),
  );
  return button;
}

function renderDetail() {
  if (state.runs.length === 0) {
    setChildren(els.runDetail, [empty("暂无运行记录")]);
    return;
  }
  if (state.lastError && !state.detail) {
    setChildren(els.runDetail, [errorNode(state.lastError)]);
    return;
  }
  if (!state.detail) {
    setChildren(els.runDetail, [empty("请选择一个运行")]);
    return;
  }

  const detail = state.detail;
  const nodes = [];
  if (state.lastError) {
    nodes.push(errorNode(state.lastError));
  }
  const grid = el("div", "detail-grid");
  [
    ["任务描述", detail.task_summary, "wide"],
    ["运行 ID", detail.run_id, ""],
    ["策略", policyLabel(detail.policy), ""],
    ["阶段", phaseLabel(detail.phase), ""],
    ["健康状态", healthLabel(detail.health), ""],
    ["下一动作", actionLabel(detail.next_action), "wide"],
    ["最后结果", resultLabel(detail.last_result), "wide"],
    ["停止条件", listText(detail.stop_conditions), "wide"],
    ["允许路径", listText(detail.allowed_paths || detail.artifact_paths), "wide"],
  ].forEach(([label, value, extra]) => {
    const item = el("div", `detail-item${extra ? ` ${extra}` : ""}`);
    item.append(el("div", "detail-label", label), el("div", "detail-value", text(value)));
    grid.append(item);
  });
  nodes.push(grid);
  setChildren(els.runDetail, nodes);
}

function renderFlow() {
  const nodes = state.detail && Array.isArray(state.detail.flow_nodes) ? state.detail.flow_nodes : [];
  if (nodes.length === 0) {
    setChildren(els.flowDiagram, [empty("等待运行数据")]);
    return;
  }
  setChildren(els.flowDiagram, nodes.map((node) => {
    const status = text(node.status, "waiting");
    const block = el("div", `flow-node status-${status}`);
    block.append(
      el("div", "flow-node-title", text(node.label)),
      el("div", `status-pill status-${status}`, statusLabel(status)),
      el("div", "flow-hint", flowHint(node, state.detail)),
    );
    return block;
  }));
}

function renderAgents() {
  const agents = state.detail && state.detail.agents ? state.detail.agents : {};
  const names = ["planner", "generator", "evaluator"];
  if (!names.some((name) => agents[name])) {
    setChildren(els.agentCards, [empty("等待 Agent 数据")]);
    return;
  }
  setChildren(els.agentCards, names.map((name) => {
    const agent = agents[name] || {};
    const card = el("article", "agent-card");
    const title = el("div", "agent-title");
    title.append(el("span", "", AGENT_LABELS[name] || name), el("span", "badge", `尝试 ${agent.attempt || 0}`));
    card.append(
      title,
      el("div", "agent-field", `状态：${agentStatusLabel(agent.status)}`),
      el("div", "agent-field", `当前动作：${actionLabel(agent.current_action)}`),
      el("div", "agent-result", `最后结果：${text(agent.last_result)}`),
    );
    return card;
  }));
}

function renderDiagnostics() {
  const diagnostics = state.detail && Array.isArray(state.detail.blocked_diagnostics) ? state.detail.blocked_diagnostics : [];
  if (diagnostics.length === 0) {
    setChildren(els.diagnostics, [empty("暂无阻塞诊断")]);
    return;
  }
  setChildren(els.diagnostics, diagnostics.map((item) => {
    const node = el("article", "diagnostic");
    const evidence = Array.isArray(item.evidence) && item.evidence.length ? `证据：${item.evidence.join("；")}` : "";
    node.append(
      el("div", "diagnostic-title", `${text(item.title || item.kind)} · ${severityLabel(item.severity)}`),
      el("div", "diagnostic-message", text(item.message || evidence)),
      el("div", "diagnostic-source", text(item.source)),
    );
    if (evidence && item.message) {
      node.append(el("div", "diagnostic-source", evidence));
    }
    return node;
  }));
}

function renderLogs() {
  const kind = els.kindFilter.value;
  const keyword = els.keywordFilter.value.trim().toLowerCase();
  const allEntries = combinedLogEntries();
  let entries = allEntries.filter((entry) => {
    const entryKind = entry.kind || entry.stream || "log";
    const kindMatches = kind === "all" || entryKind === kind || entry.stream === kind;
    const haystack = `${entryKind} ${entry.source || ""} ${entry.message || ""} ${entry.content || ""}`.toLowerCase();
    return kindMatches && (!keyword || haystack.includes(keyword));
  });
  if (entries.length === 0 && keyword) {
    entries = allEntries.filter((entry) => {
      const entryKind = entry.kind || entry.stream || "log";
      const haystack = `${entryKind} ${entry.source || ""} ${entry.message || ""} ${entry.content || ""}`.toLowerCase();
      return haystack.includes(keyword);
    });
  }

  if (entries.length === 0) {
    setChildren(els.logList, [empty("没有匹配的日志或事件")]);
    return;
  }

  setChildren(els.logList, entries.map((entry) => {
    const isEvent = entry.type === "event";
    const block = el("article", `log-entry${isEvent ? " event-entry" : ""}`);
    const meta = el("div", "log-meta");
    meta.append(
      el("span", "log-source", `${entry.kind || entry.stream || "log"} · ${text(entry.source)}`),
      el("span", "", formatTime(entry.updated_at)),
    );
    block.append(meta, el("pre", "log-content", text(entry.content || entry.message)));
    return block;
  }));
}

function combinedLogEntries() {
  const events = state.events.map((event) => ({ ...event, type: "event" }));
  const logs = state.logs.map((log) => ({ ...log, kind: log.stream || "log", type: "log" }));
  return [...events, ...logs].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

function renderErrorState() {
  renderProject();
  if (state.runs.length === 0) {
    setChildren(els.runList, [errorNode(state.lastError)]);
  }
  if (!state.detail) {
    setChildren(els.runDetail, [errorNode(state.lastError)]);
  }
}

function policyLabel(policy) {
  const labels = {
    demand_development: "需求开发循环",
    autonomous_knowledge: "自主知识循环",
  };
  return labels[policy] || text(policy);
}

function actionLabel(action) {
  const labels = {
    run_generator: "运行 Generator",
    run_generator_repair: "Generator 修复",
    repair_and_reevaluate: "修复后回到 Evaluator",
    run_evaluator: "运行 Evaluator",
    await_human_merge_confirmation: "等待人工合并确认",
    proceed_to_user_acceptance: "进入用户验收",
  };
  return labels[action] || text(action);
}

function resultLabel(result) {
  const labels = {
    pass: "通过",
    fail: "失败",
    failed: "失败",
    blocked: "阻塞",
    invalid_artifact: "产物无效",
    none: "暂无",
  };
  return labels[result] || text(result);
}

function agentStatusLabel(status) {
  const labels = {
    ready: "就绪",
    missing: "未发现产物",
    implemented: "已实现",
    pass: "通过",
    fail: "失败",
    failed: "失败",
    blocked: "阻塞",
  };
  return labels[status] || text(status);
}

function severityLabel(severity) {
  const labels = {
    critical: "严重",
    major: "主要",
    minor: "次要",
  };
  return labels[severity] || text(severity);
}

function listText(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join("；") : "暂无";
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return text(value);
}

function flowHint(node, detail) {
  const status = node.status;
  const id = node.id || "";
  if (status === "blocked") {
    return id === "evaluator" ? "Evaluator 阻塞，修复后回到 Planner 或 Generator" : "需要处理阻塞后继续";
  }
  if (status === "running") {
    return `当前动作：${actionLabel(detail && detail.next_action)}`;
  }
  if (id === "human_merge" && detail && detail.phase === "passed_waiting_human_merge") {
    return "等待人工确认合并";
  }
  if (id === "planner" && detail && String(detail.next_action || "").includes("repair")) {
    return "修复需要时可回到 Planner 调整计划";
  }
  return statusLabel(status);
}

function formatTime(value) {
  if (!value) {
    return "暂无时间";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function setPollState(message) {
  els.pollState.textContent = message;
}

els.kindFilter.addEventListener("change", renderLogs);
els.keywordFilter.addEventListener("input", renderLogs);

refresh();
state.pollTimer = window.setInterval(refresh, POLL_MS);
