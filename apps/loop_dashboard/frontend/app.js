const POLL_MS = 3000;
const COMPLETED_PHASES = new Set([
  "passed_waiting_human_merge",
  "stopped_no_action",
  "stopped_budget",
  "stopped_blocked",
]);

const PHASE_LABELS = {
  passed_waiting_human_merge: "通过，等待人工合并",
  child_running: "子任务运行中",
  generating: "生成中",
  passed: "通过",
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
  partial: "部分完成",
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
  auditor: "Auditor",
};

const ACTION_LABELS = {
  run_parent_planner: "运行父 Planner",
  run_child_planner: "运行子任务 Planner",
  run_child_generator: "运行子任务 Generator",
  resume_current_child: "继续当前子任务",
  repair_child: "修复子任务",
  return_to_parent_planner: "返回父 Planner",
  run_generator: "运行 Generator",
  run_generator_repair: "Generator 修复",
  repair_and_reevaluate: "修复后回到 Evaluator",
  run_evaluator: "运行 Evaluator",
  await_human_merge_confirmation: "等待人工合并确认",
  proceed_to_user_acceptance: "进入用户验收",
  refocus: "重新聚焦",
  switch_task: "切换任务",
  stop_early: "提前停止",
  ask_user: "请求用户决策",
  continue: "继续",
  none: "暂无",
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
  activeTab: "overview",
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
  runDetailHeading: document.getElementById("run-detail-heading"),
  runDetail: document.getElementById("run-detail-content"),
  detailTabs: document.getElementById("detail-tabs"),
  tabPanels: Array.from(document.querySelectorAll(".tab-panel")),
  childrenContent: document.getElementById("children-content"),
  acceptanceContent: document.getElementById("acceptance-content"),
  auditorContent: document.getElementById("auditor-content"),
  artifactContent: document.getElementById("artifact-content"),
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

function runKindLabel(runKind) {
  const labels = { parent: "父需求", child: "子任务", single: "单任务" };
  return labels[runKind] || "单任务";
}

function childrenProgressLabel(summary) {
  if (!summary || !summary.total) {
    return "无子任务";
  }
  return `${summary.passed || 0} / ${summary.total || 0} 通过`;
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

function auditVerdictLabel(verdict) {
  const labels = {
    pass: "通过",
    must_fix: "必须整改",
    should_fix: "建议整改",
    observe: "观察",
    blocked: "审计不可用",
  };
  return labels[verdict] || text(verdict, "暂无审计");
}

function auditStatusLabel(status) {
  const labels = {
    available: "已生成审计",
    missing: "暂无审计",
    invalid_artifact: "审计产物无效",
  };
  return labels[status] || text(status);
}

function auditBadgeClass(verdict, openMustFix) {
  if (Number(openMustFix) > 0 || verdict === "must_fix") {
    return "status-blocked";
  }
  if (verdict === "pass") {
    return "status-done";
  }
  return "status-running";
}

function signalLabel(key) {
  const labels = {
    passed_children_since_last_audit: "通过子任务",
    autonomous_rounds_since_last_audit: "自治轮次",
    commits_since_last_audit: "新增提交",
    coverage_layers_changed: "覆盖层变化",
    new_raw_files: "新增 raw",
    new_or_updated_wiki_pages: "更新 wiki",
    same_evaluator_finding_count: "重复 finding",
    same_dirty_path_count: "重复 dirty path",
    same_identity_key_blocked_count: "重复 blocked key",
    same_file_modified_consecutively: "连续修改同文件",
    unclassified_dirty_paths: "未归属 dirty paths",
    unpushed_commits: "未推送 commit",
    missing_required_evidence: "缺失证据",
    dashboard_visibility_failures: "看板可见性失败",
    same_local_issue_rounds: "同一局部问题轮次",
  };
  return labels[key] || key.replaceAll("_", " ");
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

function setActiveTab(tabName) {
  const validTabs = ["overview", "children", "agents", "acceptance", "auditor", "logs", "diagnostics", "artifacts"];
  state.activeTab = validTabs.includes(tabName) ? tabName : "overview";
  renderTabs();
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
  if (state.selectedRunId !== runId) {
    state.activeTab = "overview";
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
  renderTabs();
  renderFlow();
  renderChildrenTab();
  renderAgents();
  renderAcceptanceTab();
  renderAuditorTab();
  renderDiagnostics();
  renderArtifacts();
  renderLogs();
}

function renderProject() {
  if (!state.project) {
    setChildren(els.projectStatus, [empty("正在读取项目状态...")]);
    return;
  }
  const rows = [
    ["项目", state.project.project_root],
    ["运行目录", state.project.loop_runs_path],
  ].map(([key, value]) => {
    const item = el("div", "project-strip-item");
    item.append(el("span", "project-strip-label", `${key}：`), el("span", "project-strip-value", text(value)));
    return item;
  });
  setChildren(els.projectStatus, rows);
}

function renderRunLists() {
  if (state.runs.length === 0) {
    setChildren(els.runList, [empty("暂无运行记录。等待 .codex/loop-runs 生成后会自动刷新。")]);
    setChildren(els.completedRuns, [empty("暂无已完成运行")]);
    return;
  }

  setChildren(els.runList, state.runs.map((run) => runButton(run)));
  setChildren(els.completedRuns, []);
}

function runButton(run) {
  const button = el("button", `run-button${run.run_id === state.selectedRunId ? " is-selected" : ""}`);
  button.type = "button";
  button.dataset.runId = run.run_id;
  button.setAttribute("aria-pressed", run.run_id === state.selectedRunId ? "true" : "false");
  button.addEventListener("click", () => selectRun(run.run_id));

  const topline = el("div", "run-topline");
  topline.append(el("span", "run-id", text(run.run_id)));
  topline.append(el("span", `badge health-${text(run.health, "progressing")}`, healthLabel(run.health)));

  const metaParts = [runKindLabel(run.run_kind), phaseLabel(run.phase), formatTime(run.updated_at)];
  if (run.run_kind === "parent") {
    metaParts.splice(1, 0, childrenProgressLabel(run.children_summary));
  }

  button.append(
    topline,
    el("div", "run-summary", text(run.task_summary)),
    el("div", "run-meta", metaParts.join(" · ")),
  );
  if (run.run_kind === "parent" && run.current_child_run_id) {
    button.append(el("div", "run-child-current", `当前子任务：${run.current_child_run_id}`));
  }
  return button;
}

function renderDetail() {
  setChildren(els.runDetailHeading, []);
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

  const heading = el("div", "run-detail-title");
  heading.append(
    el("h2", "", text(detail.run_id)),
    el("span", `badge health-${text(detail.health, "progressing")}`, healthLabel(detail.health)),
  );
  setChildren(els.runDetailHeading, [heading]);

  const summary = el("section", "run-summary-card");
  summary.append(
    el("div", "detail-section-title", "任务摘要"),
    el("div", "task-summary-text", text(detail.task_description || detail.task_summary)),
  );

  const decision = detail.decision_summary || {};
  const decisionGrid = el("div", "decision-grid");
  [
    ["当前进展", phaseLabel(detail.phase)],
    ["下一步", actionLabel(detail.next_action)],
    ["用户决策", decision.requires_user_decision ? "需要" : "不需要"],
  ].forEach(([label, value]) => {
    decisionGrid.append(summaryMetric(label, value));
  });
  summary.append(decisionGrid);
  if (detail.run_kind === "parent") {
    summary.append(renderParentReaderSummary(detail), renderChildQueue(detail.children || []));
  }

  const info = el("section", "run-info-card");
  info.append(el("div", "detail-section-title", "运行信息"));
  const infoGrid = el("div", "run-info-grid");
  [
    ["ID", detail.run_id],
    ["策略", policyLabel(detail.policy)],
    ["阶段", phaseLabel(detail.phase)],
    ["健康状态", healthLabel(detail.health)],
    ["来源", detail.source_path],
  ].forEach(([label, value]) => {
    infoGrid.append(infoRow(label, value));
  });
  info.append(infoGrid);

  nodes.push(summary, info);
  setChildren(els.runDetail, nodes);
}

function summaryMetric(label, value) {
  const item = el("div", "summary-metric");
  item.append(el("div", "summary-metric-label", label), el("div", "summary-metric-value", text(value)));
  return item;
}

function infoRow(label, value) {
  const row = el("div", "run-info-row");
  row.append(el("span", "run-info-label", `${label}:`), el("span", "run-info-value", text(value)));
  return row;
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

function renderParentReaderSummary(detail) {
  const summary = detail.reader_summary || {};
  const section = el("section", "parent-reader-summary");
  section.append(el("div", "detail-section-title", "父需求读者摘要"));
  [
    ["目的", summary.purpose || detail.task_description || detail.task_summary],
    ["当前进展", parentProgressText(detail, summary.current_progress)],
    ["下一步", parentNextStepText(detail, summary.next_step)],
    ["用户决策", parentDecisionText(detail, summary.decision_needed)],
  ].forEach(([label, value]) => section.append(infoRow(label, value)));
  return section;
}

function renderChildQueue(children) {
  const section = el("section", "child-queue");
  section.append(el("div", "detail-section-title", "子任务队列"));
  if (!children.length) {
    section.append(empty("暂无子任务"));
    return section;
  }
  children.forEach((child) => {
    const card = el("article", "child-card");
    const reader = child.reader_summary || {};
    const titlePrefix = childIndexPrefix(child.child_index);
    card.append(
      el("div", "child-card-title", `${titlePrefix}${text(child.task_description || child.task_summary || child.run_id)}`),
      el("div", "child-card-meta", `${phaseLabel(child.phase)} · ${text(child.run_id)}`),
      childReaderRow("Planner", reader.planner_action),
      childReaderRow("Generator", reader.generator_action),
      childReaderRow("Evaluator", reader.evaluator_action),
      childReaderRow("验收", reader.acceptance_result),
    );
    section.append(card);
  });
  return section;
}

function childIndexPrefix(childIndex) {
  const normalized = Number(childIndex);
  return Number.isFinite(normalized) && normalized !== 0 ? `${normalized}. ` : "";
}

function childReaderRow(label, value) {
  const row = el("div", "child-reader-row");
  row.append(el("span", "child-reader-label", `${label}:`), el("span", "child-reader-value", text(value, "暂无")));
  return row;
}

function renderChildrenTab() {
  if (!els.childrenContent) {
    return;
  }
  if (!state.detail) {
    setChildren(els.childrenContent, [empty("暂无子任务")]);
    return;
  }
  if (state.detail.run_kind !== "parent") {
    setChildren(els.childrenContent, [empty("当前运行不是父需求，没有子任务树。")]);
    return;
  }
  const children = Array.isArray(state.detail.children) ? state.detail.children : [];
  const section = el("section", "children-tab-content");
  section.append(el("div", "detail-section-title", "子任务详情"));
  if (!children.length) {
    section.append(empty("父 Planner 尚未生成可展示的子任务。"));
    setChildren(els.childrenContent, [section]);
    return;
  }
  children.forEach((child) => section.append(childDetailCard(child)));
  setChildren(els.childrenContent, [section]);
}

function childDetailCard(child) {
  const reader = child.reader_summary || {};
  const status = childVisualStatus(child);
  const card = el("article", `child-detail-card status-${status}`);
  const header = el("div", "child-detail-header");
  header.append(
    el("div", "child-detail-title", `${childIndexPrefix(child.child_index)}${text(child.task_description || child.task_summary || child.run_id)}`),
    el("span", `status-pill status-${status}`, phaseLabel(child.phase)),
  );
  card.append(
    header,
    el("div", "child-detail-meta", text(child.run_id)),
    parentStepRow("Planner", reader.planner_action || agentResult(child, "planner")),
    parentStepRow("Generator", reader.generator_action || agentResult(child, "generator")),
    parentStepRow("Evaluator", reader.evaluator_action || agentResult(child, "evaluator")),
    parentStepRow("验收", reader.acceptance_result || resultLabel(child.last_result)),
  );
  const diagnostics = Array.isArray(child.blocked_diagnostics) ? child.blocked_diagnostics : [];
  if (diagnostics.length) {
    const diag = el("div", "child-detail-diagnostics");
    diag.append(el("div", "artifact-title", "失败或阻塞原因"));
    diagnostics.forEach((item) => {
      diag.append(el("div", "child-detail-diagnostic", `${text(item.title || item.kind)}：${text(item.message || item.reason)}`));
    });
    card.append(diag);
  }
  card.append(artifactList(childArtifactPaths(child), "child-detail-artifacts"));
  return card;
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

function renderTabs() {
  if (!els.detailTabs) {
    return;
  }
  const buttons = Array.from(els.detailTabs.querySelectorAll("[data-tab]"));
  buttons.forEach((button) => {
    const selected = button.dataset.tab === state.activeTab;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-selected", selected ? "true" : "false");
    button.tabIndex = selected ? 0 : -1;
  });
  els.tabPanels.forEach((panel) => {
    const tabName = panel.id.replace(/^tab-/, "");
    const selected = tabName === state.activeTab;
    panel.hidden = !selected;
  });
}

function renderAcceptanceTab() {
  if (!els.acceptanceContent) {
    return;
  }
  if (!state.detail) {
    setChildren(els.acceptanceContent, [empty("暂无结构化验收场景")]);
    return;
  }
  setChildren(els.acceptanceContent, [renderAcceptanceSummary(state.detail.acceptance_summary || {})]);
}

function renderAuditorTab() {
  if (!els.auditorContent) {
    return;
  }
  if (!state.detail) {
    setChildren(els.auditorContent, [empty("暂无审计与 Skill 数据")]);
    return;
  }
  setChildren(els.auditorContent, [
    renderAuditSummary(state.detail.audit_summary || {}),
    renderSkillInventory(state.detail.skill_inventory || {}),
  ]);
}

function renderAuditSummary(summary) {
  const wrapper = el("section", "auditor-section");
  const title = el("div", "reader-summary-title");
  title.append(
    el("span", "", "Auditor 审计"),
    el("span", `badge ${auditBadgeClass(summary.verdict, summary.open_must_fix)}`, auditVerdictLabel(summary.verdict)),
  );
  wrapper.append(title);

  const metrics = el("div", "audit-metrics");
  [
    ["状态", auditStatusLabel(summary.status)],
    ["结论", auditVerdictLabel(summary.verdict)],
    ["open must_fix", String(Number(summary.open_must_fix) || 0)],
    ["方向控制", actionLabel(summary.direction_action)],
  ].forEach(([label, value]) => metrics.append(summaryMetric(label, value)));
  wrapper.append(metrics);

  const reason = text(summary.direction_reason || summary.recommended_next_focus, "");
  if (reason) {
    wrapper.append(el("div", "auditor-note", reason));
  }
  const reportPath = text(summary.latest_report_path, "");
  if (reportPath) {
    wrapper.append(el("div", "auditor-artifact", `审计产物：${reportPath}`));
  }

  wrapper.append(renderSignalMetrics(summary.signals || {}), renderAuditFindings(summary.findings || []));
  return wrapper;
}

function renderSignalMetrics(signals) {
  const section = el("section", "auditor-subsection");
  section.append(el("div", "detail-section-title", "确定性信号"));
  const entries = Object.entries(signals || {}).slice(0, 8);
  if (!entries.length) {
    section.append(empty("暂无 deterministic signals。Auditor 不能在缺少确定性信号时触发 must_fix。"));
    return section;
  }
  const grid = el("div", "signal-grid");
  entries.forEach(([key, value]) => {
    grid.append(summaryMetric(signalLabel(key), String(value)));
  });
  section.append(grid);
  return section;
}

function renderAuditFindings(findings) {
  const section = el("section", "auditor-subsection");
  section.append(el("div", "detail-section-title", "审计发现"));
  if (!Array.isArray(findings) || findings.length === 0) {
    section.append(empty("暂无 open audit finding。"));
    return section;
  }
  const list = el("div", "audit-finding-list");
  findings.forEach((finding) => {
    const card = el("article", "audit-finding");
    card.append(
      el("div", "audit-finding-title", `${text(finding.finding_id, "audit finding")} · ${text(finding.severity, "observe")}`),
      el("div", "audit-finding-heading", text(finding.title)),
      el("div", "audit-finding-summary", text(finding.summary)),
    );
    list.append(card);
  });
  section.append(list);
  return section;
}

function renderSkillInventory(inventory) {
  const wrapper = el("section", "auditor-section");
  const title = el("div", "reader-summary-title");
  title.append(el("span", "", "当前项目 Skill 使用情况"), el("span", "badge status-running", "repo hygiene cadence"));
  wrapper.append(title);

  const metrics = el("div", "skill-metrics");
  [
    ["项目 Skill", String(Number(inventory.total_project_skills) || 0)],
    ["Loop 相关", String(Number(inventory.loop_related_skills) || 0)],
    ["近期调用", String(Number(inventory.used_recently) || 0)],
    ["候选沉淀", String(Number(inventory.candidate_skills) || 0)],
  ].forEach(([label, value]) => metrics.append(summaryMetric(label, value)));
  wrapper.append(metrics);

  const items = Array.isArray(inventory.items) ? inventory.items : [];
  if (!items.length) {
    wrapper.append(empty("暂无项目 Skill。"));
    return wrapper;
  }
  const table = el("div", "skill-table-wrap");
  const tableNode = document.createElement("table");
  tableNode.className = "skill-table";
  const thead = document.createElement("thead");
  const header = document.createElement("tr");
  ["Skill", "来源", "用途", "Auditor 建议"].forEach((label) => header.append(el("th", "", label)));
  thead.append(header);
  const tbody = document.createElement("tbody");
  items.slice(0, 20).forEach((item) => {
    const row = document.createElement("tr");
    row.append(
      el("td", "", text(item.name)),
      el("td", "", text(item.source_path)),
      el("td", "", text(item.description, item.kind === "candidate" ? "候选流程规范" : "暂无描述")),
      el("td", "", text(item.recommendation)),
    );
    tbody.append(row);
  });
  tableNode.append(thead, tbody);
  table.append(tableNode);
  wrapper.append(table);
  return wrapper;
}

function renderArtifacts() {
  if (!els.artifactContent) {
    return;
  }
  if (!state.detail) {
    setChildren(els.artifactContent, [empty("暂无产物路径")]);
    return;
  }
  const sections = [];
  sections.push(artifactSection("运行产物", normalizeList(state.detail.artifact_paths)));
  const flowPaths = [];
  (Array.isArray(state.detail.flow_nodes) ? state.detail.flow_nodes : []).forEach((node) => {
    flowPaths.push(...normalizeList(node.artifact_paths));
  });
  sections.push(artifactSection("流程产物", Array.from(new Set(flowPaths))));
  const agentPaths = [];
  Object.values(state.detail.agents || {}).forEach((agent) => {
    agentPaths.push(...agentArtifactPaths(agent || {}));
  });
  sections.push(artifactSection("Agent 产物", Array.from(new Set(agentPaths))));
  setChildren(els.artifactContent, sections);
}

function artifactSection(title, paths) {
  const wrapper = el("section", "artifact-section");
  wrapper.append(el("div", "detail-section-title", title), artifactList(paths));
  return wrapper;
}

function renderFlow() {
  const isParentRun = state.detail && state.detail.run_kind === "parent";
  els.flowDiagram.classList.toggle("is-parent-flow", Boolean(isParentRun));
  if (isParentRun) {
    renderParentFlow(state.detail);
    return;
  }

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
  const isParentRun = state.detail && state.detail.run_kind === "parent";
  els.agentCards.classList.toggle("is-parent-agents", Boolean(isParentRun));
  if (isParentRun) {
    renderParentAgents(state.detail);
    return;
  }

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

function renderParentFlow(detail) {
  const children = Array.isArray(detail.children) ? detail.children : [];
  const summary = detail.children_summary || detail.aggregate_acceptance || {};
  const wrapper = el("div", "parent-flow-overview");

  const progress = el("section", "parent-flow-summary");
  progress.append(el("div", "detail-section-title", "父需求进展"));
  const metrics = el("div", "parent-flow-metrics");
  [
    ["子任务进度", parentChildrenProgressText(summary)],
    ["当前子任务", detail.current_child_run_id || "等待父 Planner 选择"],
    ["下一步", actionLabel(detail.next_action)],
    ["用户决策", detail.decision_summary && detail.decision_summary.requires_user_decision ? "需要" : "不需要"],
  ].forEach(([label, value]) => metrics.append(summaryMetric(label, value)));
  progress.append(metrics);

  const childSection = el("section", "parent-flow-children");
  childSection.append(el("div", "detail-section-title", "子任务运行概览"));
  if (!children.length) {
    childSection.append(empty("父 Planner 尚未生成可展示的子任务。"));
  } else {
    const grid = el("div", "parent-flow-child-grid");
    children.forEach((child) => grid.append(parentFlowChildCard(child)));
    childSection.append(grid);
  }

  wrapper.append(progress, childSection);
  setChildren(els.flowDiagram, [wrapper]);
}

function parentFlowChildCard(child) {
  const reader = child.reader_summary || {};
  const status = childVisualStatus(child);
  const card = el("article", `parent-flow-child status-${status}`);
  const header = el("div", "parent-flow-child-header");
  header.append(
    el("div", "parent-flow-child-title", `${childIndexPrefix(child.child_index)}${text(child.task_description || child.task_summary || child.run_id)}`),
    el("span", `status-pill status-${status}`, phaseLabel(child.phase)),
  );
  card.append(
    header,
    el("div", "parent-flow-child-meta", text(child.run_id)),
    parentStepRow("Planner", reader.planner_action || agentResult(child, "planner")),
    parentStepRow("Generator", reader.generator_action || agentResult(child, "generator")),
    parentStepRow("Evaluator", reader.evaluator_action || agentResult(child, "evaluator")),
    parentStepRow("验收", reader.acceptance_result || resultLabel(child.last_result)),
  );
  return card;
}

function parentProgressText(detail, value) {
  const normalized = text(value, "");
  if (!normalized || normalized === detail.phase || /children passed/i.test(normalized)) {
    return parentChildrenProgressText(detail.children_summary || detail.aggregate_acceptance || {});
  }
  return readableLooseText(normalized);
}

function parentNextStepText(detail, value) {
  const normalized = text(value, "");
  if (!normalized || normalized === detail.next_action || ACTION_LABELS[normalized] || /^run |^await |^resume |^repair/i.test(normalized)) {
    return actionLabel(detail.next_action || normalized);
  }
  return readableLooseText(normalized);
}

function parentDecisionText(detail, value) {
  const normalized = text(value, "");
  if (!normalized || /^(no|false)$/i.test(normalized)) {
    const decision = detail.decision_summary || {};
    return decision.requires_user_decision ? "需要" : "不需要";
  }
  if (/^(yes|true)$/i.test(normalized)) {
    return "需要";
  }
  return readableLooseText(normalized);
}

function readableLooseText(value) {
  const raw = text(value, "");
  const labels = {
    "1 children passed": "1 个子任务已通过",
    "2 children passed": "2 个子任务已通过",
    "3 children passed": "3 个子任务已通过",
    "Run parent planner": "运行父 Planner",
    "Await human merge": "等待人工合并确认",
    "No": "不需要",
    "Yes": "需要",
    child_running: "子任务运行中",
  };
  return labels[raw] || actionLabel(raw);
}

function renderParentAgents(detail) {
  const children = Array.isArray(detail.children) ? detail.children : [];
  const nodes = [];
  const summary = el("section", "parent-agent-summary");
  summary.append(
    el("div", "detail-section-title", "父需求 Agent 结果"),
    el("div", "parent-agent-note", "按子任务聚合展示 Planner、Generator、Evaluator 做了什么，便于判断整个需求 loop 推进到哪里。"),
  );
  const parentPlanner = detail.agents && detail.agents.planner ? detail.agents.planner : null;
  if (parentPlanner) {
    summary.append(parentStepRow("父 Planner", parentPlanner.last_result || detail.task_summary));
  }
  nodes.push(summary);

  if (!children.length) {
    nodes.push(empty("父 Planner 尚未生成可展示的子任务 Agent 结果。"));
    setChildren(els.agentCards, nodes);
    return;
  }

  children.forEach((child) => nodes.push(parentAgentChildCard(child)));
  setChildren(els.agentCards, nodes);
}

function parentAgentChildCard(child) {
  const reader = child.reader_summary || {};
  const status = childVisualStatus(child);
  const card = el("article", `parent-agent-card status-${status}`);
  const header = el("div", "parent-agent-child-header");
  header.append(
    el("div", "parent-agent-child-title", `${childIndexPrefix(child.child_index)}${text(child.task_description || child.task_summary || child.run_id)}`),
    el("span", `status-pill status-${status}`, phaseLabel(child.phase)),
  );
  card.append(header, el("div", "parent-agent-child-meta", text(child.run_id)));

  [
    ["planner", reader.planner_action],
    ["generator", reader.generator_action],
    ["evaluator", reader.evaluator_action],
  ].forEach(([name, readerAction]) => {
    card.append(parentAgentRow(name, child.agents && child.agents[name], readerAction));
  });
  return card;
}

function parentAgentRow(name, agent, readerAction) {
  const currentAgent = agent || {};
  const row = el("div", "parent-agent-row");
  const heading = el("div", "parent-agent-row-heading");
  heading.append(
    el("span", "parent-agent-name", agentLabel(name)),
    el("span", "parent-agent-status", `${agentStatusLabel(currentAgent.status)} · 尝试 ${currentAgent.attempt || 0}`),
  );
  const body = el("div", "parent-agent-row-body");
  body.append(el("div", "parent-agent-action", text(readerAction || currentAgent.last_result)));
  const paths = agentArtifactPaths(currentAgent);
  if (paths.length) {
    body.append(artifactList(paths, "parent-agent-artifacts"));
  }
  row.append(heading, body);
  return row;
}

function parentStepRow(label, value) {
  const row = el("div", "parent-step-row");
  row.append(el("span", "parent-step-label", `${label}:`), el("span", "parent-step-value", text(value)));
  return row;
}

function parentChildrenProgressText(summary) {
  const total = Number(summary && summary.total) || 0;
  if (!total) {
    return "暂无子任务";
  }
  const passed = Number(summary.passed) || 0;
  const failed = Number(summary.failed) || 0;
  const blocked = Number(summary.blocked) || 0;
  const pending = Number(summary.pending) || 0;
  const extras = [];
  if (pending) {
    extras.push(`${pending} 待处理`);
  }
  if (failed) {
    extras.push(`${failed} 失败`);
  }
  if (blocked) {
    extras.push(`${blocked} 阻塞`);
  }
  return extras.length ? `${passed} / ${total} 通过，${extras.join("，")}` : `${passed} / ${total} 通过`;
}

function childVisualStatus(child) {
  const phase = String(child && child.phase || "");
  const lastResult = String(child && child.last_result || "");
  if (["passed", "passed_waiting_human_merge"].includes(phase) || lastResult === "pass") {
    return "done";
  }
  if (["stopped_blocked", "repair_needed", "invalid_artifact", "failed", "fail"].includes(phase) || ["blocked", "fail", "failed"].includes(lastResult)) {
    return "blocked";
  }
  if (["generating", "child_running", "running"].includes(phase) || String(child && child.next_action || "").startsWith("run_")) {
    return "running";
  }
  return "waiting";
}

function agentResult(child, name) {
  const agent = child && child.agents && child.agents[name] ? child.agents[name] : {};
  return agent.last_result || "";
}

function childArtifactPaths(child) {
  const paths = [
    ...normalizeList(child.artifact_paths),
    ...normalizeList(child.allowed_paths),
  ];
  Object.values(child.agents || {}).forEach((agent) => {
    paths.push(...agentArtifactPaths(agent || {}));
  });
  return Array.from(new Set(paths));
}

function renderDiagnostics() {
  const relationshipDiagnostics = state.detail && Array.isArray(state.detail.relationship_diagnostics) ? state.detail.relationship_diagnostics : [];
  const diagnostics = dedupeDiagnostics([
    ...(state.detail && Array.isArray(state.detail.blocked_diagnostics) ? state.detail.blocked_diagnostics : []),
    ...relationshipDiagnostics,
  ]);
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

function dedupeDiagnostics(diagnostics) {
  const seen = new Set();
  return diagnostics.filter((item) => {
    const diagnostic = item && typeof item === "object" ? item : {};
    const evidence = Array.isArray(diagnostic.evidence)
      ? diagnostic.evidence.map((value) => text(value, "")).join("；")
      : text(diagnostic.evidence, "");
    const key = [
      diagnostic.kind,
      diagnostic.title,
      diagnostic.message,
      diagnostic.source,
      evidence,
      diagnostic.severity,
    ].map((value) => text(value, "")).join("|");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
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
  return ACTION_LABELS[action] || text(action);
}

function resultLabel(result) {
  if (ACTION_LABELS[result]) {
    return ACTION_LABELS[result];
  }
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
els.detailTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-tab]");
  if (button) {
    setActiveTab(button.dataset.tab);
  }
});

refresh();
state.pollTimer = window.setInterval(refresh, POLL_MS);
