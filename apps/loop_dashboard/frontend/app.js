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
  skipped: "跳过",
};

const ACCEPTANCE_LABELS = {
  pass: "通过",
  passed: "通过",
  fail: "失败",
  failed: "失败",
  blocked: "阻塞",
  missing: "未发现",
  unknown: "未知",
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
  agentFilter: "all",
  loadingDetailFor: "",
  lastError: "",
  pollTimer: 0,
  refreshInFlight: false,
  detailRequestSeq: 0,
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
  agentFilter: document.getElementById("agent-filter"),
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

function acceptanceLabel(status) {
  return ACCEPTANCE_LABELS[status] || text(status, "未知");
}

function acceptanceStatusClass(status) {
  if (["pass", "passed"].includes(status)) {
    return "done";
  }
  if (["fail", "failed", "blocked"].includes(status)) {
    return "blocked";
  }
  return "waiting";
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

function normalizeList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => text(item, "")).filter(Boolean);
}

function agentLabel(agentName) {
  return AGENT_LABELS[agentName] || text(agentName);
}

function setAgentFilter(agentName) {
  const nextAgent = ["planner", "generator", "evaluator"].includes(agentName) ? agentName : "all";
  state.agentFilter = nextAgent;
  els.agentFilter.value = nextAgent;
  renderAgents();
  renderLogs();
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
  if (state.refreshInFlight) {
    return;
  }
  state.refreshInFlight = true;
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
      const requestedRunId = state.selectedRunId;
      await selectRun(requestedRunId, { silent: true });
      if (recoverableNotice && state.selectedRunId === requestedRunId) {
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
  } finally {
    state.refreshInFlight = false;
  }
}

async function selectRun(runId, options = {}) {
  if (!runId) {
    return;
  }
  state.selectedRunId = runId;
  state.loadingDetailFor = runId;
  const requestSeq = ++state.detailRequestSeq;
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
    if (requestSeq !== state.detailRequestSeq || state.selectedRunId !== runId) {
      return;
    }
    state.detail = detail;
    state.events = Array.isArray(eventsResponse.events) ? eventsResponse.events : [];
    state.logs = Array.isArray(logsResponse.logs) ? logsResponse.logs : [];
    state.lastError = "";
    renderAll();
  } catch (error) {
    if (requestSeq !== state.detailRequestSeq || state.selectedRunId !== runId) {
      return;
    }
    if (error.status === 404) {
      state.lastError = `选中的运行已消失：${runId}`;
      state.detail = null;
      state.events = [];
      state.logs = [];
      const fallback = state.runs.find((run) => run.run_id !== runId);
      if (fallback) {
        renderRunLists();
        setChildren(els.runDetail, [empty("正在读取备用运行详情...")]);
        await selectRun(fallback.run_id, { silent: true });
        return;
      }
    } else {
      state.lastError = `读取运行失败：${error.message}`;
    }
    renderAll();
  } finally {
    if (requestSeq === state.detailRequestSeq) {
      state.loadingDetailFor = "";
    }
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
  nodes.push(renderReaderSummary(detail));
  nodes.push(renderAcceptanceSummary(detail.acceptance_summary || {}));
  const grid = el("div", "detail-grid");
  [
    ["任务描述", detail.task_description || detail.task_summary, "long"],
    ["运行 ID", detail.run_id, "compact"],
    ["策略", policyLabel(detail.policy), "compact"],
    ["阶段", phaseLabel(detail.phase), "compact"],
    ["健康状态", healthLabel(detail.health), "compact"],
    ["下一动作", actionLabel(detail.next_action), "long"],
    ["最后结果", resultLabel(detail.last_result), "long"],
    ["停止条件", listText(detail.stop_conditions), "long"],
    ["允许路径", listText(detail.allowed_paths || detail.artifact_paths), "long"],
  ].forEach(([label, value, kind]) => {
    const item = el("div", `detail-item detail-${kind}`);
    const valueClass = kind === "long" ? "detail-value full" : "detail-value";
    item.append(el("div", "detail-label", label), el("div", valueClass, text(value)));
    grid.append(item);
  });
  nodes.push(grid);
  setChildren(els.runDetail, nodes);
}

function renderReaderSummary(detail) {
  const decision = detail.decision_summary || {};
  const wrapper = el("section", `reader-summary${decision.requires_user_decision ? " needs-decision" : ""}`);
  const titleRow = el("div", "reader-summary-title");
  titleRow.append(
    el("span", "", "任务读者摘要"),
    el("span", `badge ${decision.requires_user_decision ? "status-running" : "status-done"}`, text(decision.decision_label, "无需用户决策")),
  );
  const objective = el("div", "reader-objective", text(detail.task_description || detail.task_summary));
  const facts = el("div", "reader-facts");
  [
    ["当前进展", phaseLabel(detail.phase)],
    ["下一步", actionLabel(detail.next_action)],
    ["用户决策", decision.requires_user_decision ? "需要" : "不需要"],
    ["原因", resultLabel(decision.reason)],
  ].forEach(([label, value]) => {
    const item = el("div", "reader-fact");
    item.append(el("div", "reader-fact-label", label), el("div", "reader-fact-value", value));
    facts.append(item);
  });
  wrapper.append(titleRow, objective, facts);
  return wrapper;
}

function renderAcceptanceSummary(summary) {
  const wrapper = el("section", "acceptance-summary");
  const titleRow = el("div", "reader-summary-title");
  titleRow.append(
    el("span", "", "验收情况"),
    el("span", `badge status-${acceptanceStatusClass(summary.status)}`, acceptanceLabel(summary.status)),
  );
  wrapper.append(titleRow);

  const scenarios = Array.isArray(summary.scenarios) ? summary.scenarios : [];
  if (scenarios.length) {
    const list = el("div", "acceptance-scenarios");
    scenarios.forEach((scenario) => {
      const item = el("article", "acceptance-scenario");
      item.append(
        el("div", "acceptance-scenario-title", `${text(scenario.scenario_id || scenario.id, "未命名场景")} · ${acceptanceLabel(scenario.status)}`),
        el("div", "acceptance-scenario-summary", text(scenario.summary || scenario.user_goal || scenario.description, "暂无场景说明")),
      );
      list.append(item);
    });
    wrapper.append(list);
  } else {
    wrapper.append(empty("暂无结构化验收场景。Evaluator 运行后会在这里显示模拟用户验收内容。"));
  }

  const checked = normalizeList(summary.checked);
  if (checked.length) {
    wrapper.append(labeledList("已模拟检查的页面能力", checked, "acceptance-list"));
  }
  const evidence = normalizeList(summary.evidence);
  if (evidence.length) {
    wrapper.append(labeledList("验收证据", evidence, "acceptance-list evidence-list"));
  }
  const commands = normalizeList(summary.rerun_commands);
  if (commands.length) {
    wrapper.append(labeledList("复跑命令", commands, "acceptance-list command-list"));
  }
  return wrapper;
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
    block.title = flowNodeTitle(node);
    const header = el("div", "flow-node-header");
    header.append(
      el("div", "flow-node-title", text(node.label)),
      el("div", `status-pill status-${status}`, statusLabel(status)),
    );
    const body = el("div", "flow-node-body");
    body.append(el("div", "flow-hint", flowHint(node, state.detail)), ...flowDetailRows(node, { includeArtifacts: false }));
    const long = el("div", "flow-node-long");
    long.append(artifactList(normalizeList(node.artifact_paths), "flow-artifacts"));
    block.append(header, body, long);
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
    const card = el("button", `agent-card${state.agentFilter === name ? " is-selected" : ""}`);
    card.title = `${agentLabel(name)}\n${text(agent.last_result)}\n${agentArtifactPaths(agent).join("\n")}`;
    card.type = "button";
    card.dataset.agent = name;
    card.setAttribute("aria-pressed", state.agentFilter === name ? "true" : "false");
    card.addEventListener("click", () => setAgentFilter(name));
    const layout = el("div", "agent-card-layout");
    const main = el("div", "agent-main");
    const title = el("div", "agent-title");
    title.append(el("span", "", agentLabel(name)), el("span", "badge", `尝试 ${agent.attempt || 0}`));
    main.append(
      title,
      el("div", "agent-field", `状态：${agentStatusLabel(agent.status)}`),
      el("div", "agent-field", `当前动作：${actionLabel(agent.current_action)}`),
    );
    const longFields = el("div", "agent-long-fields");
    longFields.append(
      el("div", "agent-result", `最后结果：${text(agent.last_result)}`),
      artifactList(agentArtifactPaths(agent)),
    );
    layout.append(main, longFields);
    card.append(layout);
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
  const agent = els.agentFilter.value || state.agentFilter;
  state.agentFilter = agent;
  const keyword = els.keywordFilter.value.trim().toLowerCase();
  const allEntries = combinedLogEntries();
  const entries = allEntries.filter((entry) => {
    const entryKind = entry.kind || entry.stream || "log";
    const kindMatches = kind === "all" || entryKind === kind || entry.stream === kind;
    const entryAgent = entry.agent || inferAgent(entry);
    const agentMatches = agent === "all" || entryAgent === agent;
    const haystack = `${entryKind} ${entryAgent} ${entry.source || ""} ${entry.message || ""} ${entry.content || ""}`.toLowerCase();
    return kindMatches && agentMatches && (!keyword || haystack.includes(keyword));
  });

  if (entries.length === 0) {
    setChildren(els.logList, [empty("没有匹配的日志")]);
    return;
  }

  setChildren(els.logList, entries.map((entry) => {
    const isEvent = entry.type === "event";
    const block = el("article", `log-entry${isEvent ? " event-entry" : ""}`);
    const meta = el("div", "log-meta");
    const entryAgent = entry.agent || inferAgent(entry);
    const sourceText = entryAgent === "all"
      ? `${entry.kind || entry.stream || "log"} · ${text(entry.source)}`
      : `${agentLabel(entryAgent)} · ${entry.kind || entry.stream || "log"} · ${text(entry.source)}`;
    meta.append(
      el("span", "log-source", sourceText),
      el("span", "", formatTime(entry.updated_at)),
    );
    block.append(meta, el("pre", "log-content", text(entry.content || entry.message)));
    return block;
  }));
}

function combinedLogEntries() {
  const events = state.events.map((event) => ({ ...event, type: "event", agent: inferAgent(event) }));
  const logs = state.logs.map((log) => ({ ...log, kind: log.stream || "log", type: "log", agent: inferAgent(log) }));
  return [...events, ...logs].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

function flowDetailRows(node, options = {}) {
  const includeArtifacts = options.includeArtifacts !== false;
  const rows = [];
  if (node.current_action) {
    rows.push(el("div", "flow-detail", `动作：${actionLabel(node.current_action)}`));
  }
  if (node.recent_result) {
    rows.push(el("div", "flow-detail", `结果：${resultLabel(node.recent_result)}`));
  }
  const paths = normalizeList(node.artifact_paths);
  if (includeArtifacts && paths.length) {
    rows.push(artifactList(paths, "flow-artifacts"));
  }
  return rows;
}

function artifactList(paths, className = "artifact-list") {
  const normalized = normalizeList(paths);
  const wrapper = el("div", className);
  wrapper.append(el("div", "artifact-title", "产物路径"));
  if (normalized.length === 0) {
    wrapper.append(el("div", "artifact-empty", "暂无"));
    return wrapper;
  }
  const list = el("ul", "artifact-items");
  normalized.forEach((path) => {
    const item = el("li", "", path);
    item.title = path;
    list.append(item);
  });
  wrapper.append(list);
  return wrapper;
}

function labeledList(titleText, values, className) {
  const wrapper = el("div", className);
  wrapper.append(el("div", "artifact-title", titleText));
  const list = el("ul", "artifact-items");
  values.forEach((value) => {
    const item = el("li", "", value);
    item.title = value;
    list.append(item);
  });
  wrapper.append(list);
  return wrapper;
}

function flowNodeTitle(node) {
  const lines = [text(node.label), statusLabel(node.status)];
  if (node.current_action) {
    lines.push(`动作：${actionLabel(node.current_action)}`);
  }
  if (node.recent_result) {
    lines.push(`结果：${resultLabel(node.recent_result)}`);
  }
  lines.push(...normalizeList(node.artifact_paths));
  return lines.join("\n");
}

function agentArtifactPaths(agent) {
  const paths = [
    ...normalizeList(agent.artifact_paths),
    ...normalizeList(agent.artifacts),
    ...normalizeList(agent.changed_paths),
  ];
  return Array.from(new Set(paths));
}

function inferAgent(entry) {
  const haystack = `${entry.agent || ""} ${entry.source || ""} ${entry.message || ""} ${entry.content || ""}`.toLowerCase();
  for (const name of ["planner", "generator", "evaluator"]) {
    if (haystack.includes(name)) {
      return name;
    }
  }
  return "all";
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
  if (status === "skipped") {
    return "本次未触发";
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
els.agentFilter.addEventListener("change", () => setAgentFilter(els.agentFilter.value));
els.keywordFilter.addEventListener("input", renderLogs);

refresh();
state.pollTimer = window.setInterval(refresh, POLL_MS);
