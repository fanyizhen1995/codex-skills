const POLL_MS = 3000;
const COMPLETED_PHASES = new Set([
  "passed_waiting_human_merge",
  "stopped_no_action",
  "stopped_budget",
  "stopped_blocked",
  "audit_blocked",
]);

const PHASE_LABELS = {
  passed_waiting_human_merge: "通过，等待人工合并",
  child_running: "子任务运行中",
  generating: "生成中",
  passed: "通过",
  stopped_no_action: "停止：无需操作",
  stopped_budget: "停止：预算耗尽",
  stopped_blocked: "停止：阻塞",
  audit_blocked: "审计阻塞",
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

const SUPERVISOR_ENDPOINTS = {
  summary: "/api/supervisor",
  services: "/api/supervisor/services",
  decisions: "/api/supervisor/decisions",
  recovery: "/api/supervisor/recovery",
  required: "/api/supervisor/decision-required",
  auditor: "/api/supervisor/auditor",
};

const SUPERVISOR_STATUS_LABELS = {
  available: "可用",
  healthy: "运行正常",
  degraded: "服务异常",
  blocked: "需要处理",
  stopped: "已停止",
  open: "待处理",
  unavailable: "暂无数据",
  invalid_artifact: "产物无效",
};

const SUPERVISOR_ACTION_LABELS = {
  observe: "观察",
  resume: "恢复运行",
  restart_service: "重启服务",
  create_continuation: "创建续跑",
  request_user_decision: "请求用户决策",
  await_human_merge: "等待人工合并",
  continue: "继续",
  refocus: "重新聚焦",
  stop: "停止",
};

const SUPERVISOR_CLASSIFICATION_LABELS = {
  continuation_candidate: "续跑候选",
  active: "运行中",
  blocked: "阻塞",
  stopped: "已停止",
  human_gate: "等待人工",
  unsupported: "不支持",
  needs_user_decision: "需要用户决策",
  actionable_resume: "可恢复",
  awaiting_human_merge: "等待人工合并",
  terminal: "终止",
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
  create_audit_remediation_task: "创建审计整改子任务",
  refocus: "重新聚焦",
  switch_task: "切换任务",
  stop_early: "提前停止",
  ask_user: "请求用户决策",
  continue: "继续",
  none: "暂无",
};

const state = {
  project: null,
  supervisor: emptySupervisorBundle(),
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
  supervisorContent: document.getElementById("supervisor-content"),
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
    stop: "停止",
    continue: "继续",
    refocus: "重新聚焦",
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

function emptySupervisorBundle() {
  return {
    summary: unavailableSupervisorPayload("summary", SUPERVISOR_ENDPOINTS.summary),
    services: unavailableSupervisorPayload("services", SUPERVISOR_ENDPOINTS.services),
    decisions: unavailableSupervisorPayload("decisions", SUPERVISOR_ENDPOINTS.decisions),
    recovery: unavailableSupervisorPayload("recovery", SUPERVISOR_ENDPOINTS.recovery),
    required: unavailableSupervisorPayload("required", SUPERVISOR_ENDPOINTS.required),
    auditor: unavailableSupervisorPayload("auditor", SUPERVISOR_ENDPOINTS.auditor),
  };
}

function unavailableSupervisorPayload(key, path, error) {
  const message = error ? `读取失败：${error.message}` : "暂无数据";
  const base = {
    status: "unavailable",
    status_label: "不可用",
    diagnostics: error ? [{ source: path, status: "unavailable", message }] : [],
  };
  if (key === "summary") {
    return {
      ...base,
      state: {
        status: "unavailable",
        status_label: "暂无数据",
        service_summary: {},
        run_summary: {},
        failure_summary: {},
        service_health: {},
        last_decision: null,
        mode: "",
        last_heartbeat_at: "",
        last_tick_at: "",
        generated_at: "",
        watch_interval_seconds: null,
      },
      artifact_path: ".codex/supervisor/supervisor-state.json",
    };
  }
  if (key === "services") {
    return { ...base, checked_at: "", services: [], service_count: null };
  }
  if (key === "decisions") {
    return { ...base, decisions: [], continuation_plans: [], counts: {} };
  }
  if (key === "recovery") {
    return { ...base, attempts: [], counts: {} };
  }
  if (key === "required") {
    return { ...base, open_count: null, decisions: [], total_count: null };
  }
  if (key === "auditor") {
    return { ...base, audits: [], total_count: null, returned_count: null };
  }
  return base;
}

async function fetchSupervisorBundle() {
  const results = await Promise.all(
    Object.entries(SUPERVISOR_ENDPOINTS).map(async ([key, path]) => {
      try {
        return [key, await fetchJson(path)];
      } catch (error) {
        return [key, unavailableSupervisorPayload(key, path, error)];
      }
    }),
  );
  return Object.fromEntries(results);
}

async function refresh() {
  if (state.refreshInFlight) {
    return;
  }
  state.refreshInFlight = true;
  try {
    const [project, runs, supervisor] = await Promise.all([
      fetchJson("/api/projects/current"),
      fetchJson("/api/runs"),
      fetchSupervisorBundle(),
    ]);
    state.project = project;
    state.supervisor = supervisor;
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
  renderSupervisor();
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

function renderSupervisor() {
  if (!els.supervisorContent) {
    return;
  }
  const bundle = state.supervisor || emptySupervisorBundle();
  const nodes = [
    renderSupervisorHero(bundle),
    renderSupervisorMetrics(bundle),
    renderSupervisorTabs(),
    renderSupervisorControlFlow(bundle),
    renderSupervisorServiceDecisionGrid(bundle),
    renderSupervisorOperationalGrid(bundle),
    renderSupervisorAuditorDecisionGrid(bundle),
    renderSupervisorConfig(bundle),
    renderSupervisorDiagnostics(bundle),
  ].filter(Boolean);
  setChildren(els.supervisorContent, nodes);
}

function renderSupervisorHero(bundle) {
  const summary = bundle.summary || {};
  const snapshot = supervisorSnapshot(bundle);
  const required = bundle.required || {};
  const openCount = numberOrNull(required.open_count);
  const wrapper = el("div", "supervisor-hero");
  const textBlock = el("div", "");
  textBlock.append(
    el("h2", "", "全局 Agent：Loop Supervisor"),
    el(
      "p",
      "supervisor-summary",
      "Supervisor 是项目级运行控制面，不属于任何一个任务运行列表。它负责服务保活、运行续跑、失败升级、Dashboard 可见性和数据新鲜度；Auditor 负责判断流程质量，Supervisor 负责执行控制动作。",
    ),
  );

  const actions = el("div", "supervisor-actions");
  actions.append(
    supervisorChip(`健康状态：${supervisorStatusLabel(summary.status || snapshot.status)}`, summary.status || snapshot.status),
    supervisorChip(`人工决策：${openCountLabel(openCount)}`, openCount && openCount > 0 ? "blocked" : required.status),
    supervisorChip("独立于任务列表", "available"),
  );
  wrapper.append(textBlock, actions);
  return wrapper;
}

function renderSupervisorMetrics(bundle) {
  const snapshot = supervisorSnapshot(bundle);
  const services = supervisorServices(bundle);
  const plans = supervisorPlans(bundle);
  const serviceSummary = objectValue(snapshot.service_summary);
  const runSummary = objectValue(snapshot.run_summary);
  const version = supervisorVersionSummary(services);
  const freshness = supervisorFreshnessSummary(services);
  const totalServices = numberOrNull(serviceSummary.total);
  const healthyServices = numberOrNull(serviceSummary.healthy);
  const continuationCandidates = numberOrNull(runSummary.continuation_candidates);

  const grid = el("div", "supervisor-metrics");
  grid.append(
    supervisorMetric(
      "在线服务",
      totalServices === null || totalServices === 0 || healthyServices === null ? "不可用" : `${healthyServices} / ${totalServices}`,
      totalServices === null || totalServices === 0 ? "暂无服务汇总" : "只表示可达；版本新鲜度单独判断",
    ),
    supervisorMetric(
      "可续跑任务",
      continuationCandidates === null ? "暂无数据" : String(continuationCandidates),
      plans.length ? `${plans.length} 个续跑计划已返回` : "暂无续跑计划",
    ),
    supervisorMetric("版本新鲜度", version.value, version.note),
    supervisorMetric("数据新鲜度", freshness.value, freshness.note),
  );
  return grid;
}

function renderSupervisorTabs() {
  const tabs = ["控制面概览", "服务保活", "续跑决策", "恢复历史", "人工决策", "配置"];
  const wrapper = el("div", "supervisor-tabs");
  tabs.forEach((label, index) => {
    wrapper.append(el("span", `supervisor-tab${index === 0 ? " is-active" : ""}`, label));
  });
  return wrapper;
}

function renderSupervisorControlFlow(bundle) {
  const snapshot = supervisorSnapshot(bundle);
  const services = supervisorServices(bundle);
  const decisions = supervisorDecisions(bundle);
  const attempts = supervisorAttempts(bundle);
  const audits = supervisorAudits(bundle);
  const required = bundle.required || {};
  const lastDecision = currentSupervisorDecision(bundle);
  const runSummary = objectValue(snapshot.run_summary);
  const openCount = numberOrNull(required.open_count);
  const steps = [
    {
      title: "发现任务 run",
      detail: runSummary && Object.keys(runSummary).length
        ? `活跃=${numberText(runSummary.active)}，阻塞=${numberText(runSummary.blocked)}，续跑候选=${numberText(runSummary.continuation_candidates)}`
        : "暂无运行汇总",
      status: snapshot.status || "unavailable",
      badge: snapshot.status ? supervisorStatusLabel(snapshot.status) : "不可用",
    },
    {
      title: "检查服务",
      detail: services.length ? `${services.length} 个服务返回健康记录` : "暂无服务记录",
      status: services.length ? servicesStatus(services) : "unavailable",
      badge: services.length ? supervisorStatusLabel(servicesStatus(services)) : "不可用",
    },
    {
      title: "执行控制动作",
      detail: lastDecision ? supervisorDecisionDetail(lastDecision) : "暂无最近决策",
      status: lastDecision ? supervisorDecisionStatus(lastDecision) : "unavailable",
      badge: lastDecision ? supervisorDecisionBadge(lastDecision) : "暂无数据",
    },
    {
      title: "消费 Auditor",
      detail: audits.length ? text(audits[0].direction_reason || audits[0].recommended_next_focus || audits[0].run_id) : "暂无 Auditor 控制输入",
      status: audits.length ? audits[0].verdict || audits[0].status : "unavailable",
      badge: audits.length ? auditVerdictLabel(audits[0].verdict) : "不可用",
    },
    {
      title: "升级决策",
      detail: openCount && openCount > 0
        ? `${openCount} 条待处理人工决策`
        : attempts.length ? `${attempts.length} 条恢复尝试记录` : "暂无失败升级记录",
      status: openCount && openCount > 0 ? "blocked" : attempts.length ? "available" : "unavailable",
      badge: openCount && openCount > 0 ? "需要用户决策" : attempts.length ? "已记录" : "未启用",
    },
  ];

  const flow = el("div", "supervisor-flow");
  steps.forEach((step) => {
    const node = el("article", `supervisor-flow-step ${supervisorBoxStatusClass(step.status)}`);
    node.append(el("h3", "", step.title), el("p", "", step.detail), supervisorChip(step.badge, step.status));
    flow.append(node);
  });
  return supervisorSection("Supervisor 控制流", [flow]);
}

function renderSupervisorServiceDecisionGrid(bundle) {
  const grid = el("section", "supervisor-split");
  grid.append(renderSupervisorServices(bundle), renderSupervisorDecisionLog(bundle));
  return grid;
}

function renderSupervisorServices(bundle) {
  const services = supervisorServices(bundle);
  if (!services.length) {
    return supervisorSection("服务保活", [empty("暂无服务保活数据")]);
  }
  const list = el("div", "supervisor-list");
  services.forEach((service) => list.append(renderSupervisorServiceRow(service)));
  return supervisorSection("服务保活", [list]);
}

function renderSupervisorServiceRow(service) {
  const version = serviceVersionLabel(service);
  const row = supervisorListItem(
    serviceNameLabel(service.service),
    `${serviceReachableLabel(service)} · ${version.label}`,
    serviceBadgeStatus(service, version),
    serviceEvidence(service),
  );
  row.classList.add("supervisor-service-row");
  return row;
}

function renderSupervisorDecisionLog(bundle) {
  const decisions = supervisorDecisions(bundle);
  if (!decisions.length) {
    return supervisorSection("最近全局决策", [empty("暂无全局决策记录")]);
  }
  const list = el("div", "supervisor-decision-log");
  decisions.slice(0, 6).forEach((decision) => {
    const item = el("article", "supervisor-decision");
    item.append(
      el("span", "supervisor-decision-time", formatTime(decision.created_at || decision.recorded_at || decision.updated_at)),
      el(
        "span",
        "supervisor-decision-text",
        `${supervisorActionLabel(decision.action)}：${supervisorDecisionDetail(decision)}`,
      ),
    );
    const meta = [
      decision.run_id ? `run：${decision.run_id}` : "",
      decision.classification ? `分类=${supervisorClassificationLabel(decision.classification)}` : "",
      decision.decision_id ? `decision：${decision.decision_id}` : "",
    ].filter(Boolean);
    if (meta.length) {
      item.append(el("span", "supervisor-decision-meta", meta.join(" · ")));
    }
    list.append(item);
  });
  return supervisorSection("最近全局决策", [list]);
}

function renderSupervisorOperationalGrid(bundle) {
  const grid = el("section", "supervisor-triple");
  grid.append(
    renderSupervisorFreshness(bundle),
    renderSupervisorContinuation(bundle),
    renderSupervisorRecovery(bundle),
  );
  return grid;
}

function renderSupervisorFreshness(bundle) {
  const targets = supervisorFreshnessTargets(supervisorServices(bundle));
  if (!targets.length) {
    return supervisorSection("数据新鲜度目标", [empty("暂无数据新鲜度目标")]);
  }
  const list = el("div", "supervisor-list");
  targets.forEach((target) => {
    const details = [
      target.service ? `服务：${serviceNameLabel(target.service)}` : "",
      target.target_id ? `目标：${target.target_id}` : "",
      target.checks.length ? `检查：${target.checks.join("、")}` : "",
      target.verified_at ? `验证：${formatTime(target.verified_at)}` : "",
    ].filter(Boolean);
    list.append(supervisorListItem(target.target_id || serviceNameLabel(target.service), freshnessStatusLabel(target.status), target.status, details));
  });
  return supervisorSection("数据新鲜度目标", [list]);
}

function renderSupervisorContinuation(bundle) {
  const plans = supervisorPlans(bundle);
  if (!plans.length) {
    return supervisorSection("续跑幂等", [empty("暂无续跑计划")]);
  }
  const list = el("div", "supervisor-list");
  plans.slice(0, 6).forEach((plan) => {
    const details = [
      plan.previous_run_id ? `上一个 run：${plan.previous_run_id}` : "",
      plan.next_run_id ? `下一个 run：${plan.next_run_id}` : "",
      plan.created_at ? `创建：${formatTime(plan.created_at)}` : "",
      plan.idempotency_key ? `幂等键：${plan.idempotency_key}` : "",
      plan.idempotency_key ? "幂等：已有相同幂等键时不会重复创建续跑计划。" : "",
    ].filter(Boolean);
    list.append(supervisorListItem(plan.plan_id || plan.next_run_id || "续跑计划", text(plan.status, "暂无数据"), plan.status, details));
  });
  return supervisorSection("续跑幂等", [list]);
}

function renderSupervisorRecovery(bundle) {
  const attempts = supervisorAttempts(bundle);
  const maxFailures = numberOrNull(objectValue(supervisorSnapshot(bundle).failure_summary).max_consecutive_failures);
  if (!attempts.length) {
    return supervisorSection("失败升级", [empty("暂无恢复历史")]);
  }
  const list = el("div", "supervisor-list");
  attempts.slice(0, 6).forEach((attempt) => {
    const count = numberOrNull(attempt.consecutive_failure_count);
    const max = numberOrNull(attempt.max_consecutive_failures) || maxFailures;
    const ratio = count === null || max === null ? "暂无数据" : `${count} / ${max}`;
    const details = [
      attempt.failure_key ? `失败键：${attempt.failure_key}` : "",
      attempt.run_id ? `run：${attempt.run_id}` : "范围：project",
      attempt.action ? `动作：${supervisorActionLabel(attempt.action)}` : "",
      attempt.summary ? `摘要：${attempt.summary}` : "",
      attempt.recorded_at || attempt.finished_at || attempt.started_at ? `时间：${formatTime(attempt.recorded_at || attempt.finished_at || attempt.started_at)}` : "",
    ].filter(Boolean);
    list.append(supervisorListItem(attempt.failure_key || attempt.attempt_id || "恢复尝试", ratio, attempt.status, details));
  });
  return supervisorSection("失败升级", [list]);
}

function renderSupervisorAuditorDecisionGrid(bundle) {
  const grid = el("section", "supervisor-split");
  grid.append(renderSupervisorAuditor(bundle), renderSupervisorUserDecisions(bundle));
  return grid;
}

function renderSupervisorAuditor(bundle) {
  const audits = supervisorAudits(bundle);
  if (!audits.length) {
    return supervisorSection("Auditor 控制输入", [empty("暂无 Auditor 控制输入")]);
  }
  const list = el("div", "supervisor-list");
  audits.slice(0, 5).forEach((audit) => {
    const details = [
      audit.run_id ? `run：${audit.run_id}` : "",
      audit.direction_action ? `控制动作：${supervisorActionLabel(audit.direction_action)}` : "",
      audit.direction_reason ? `原因：${audit.direction_reason}` : "",
      audit.recommended_next_focus ? `下一焦点：${audit.recommended_next_focus}` : "",
      audit.cadence ? `审计节奏：${auditCadenceLabel(audit.cadence)}` : "",
      audit.latest_report_path ? `产物：${audit.latest_report_path}` : "",
      "边界：Supervisor 只消费 Auditor 结论，不自行判断任务质量。",
    ].filter(Boolean);
    list.append(supervisorListItem(audit.run_id || audit.latest_report_path || "Auditor", auditVerdictLabel(audit.verdict), audit.verdict, details));
  });
  return supervisorSection("Auditor 控制输入", [list]);
}

function renderSupervisorUserDecisions(bundle) {
  const required = bundle.required || {};
  const decisions = arrayValue(required.decisions);
  const openCount = numberOrNull(required.open_count);
  const heading = `待处理决策：${openCountLabel(openCount)}`;
  if (!decisions.length) {
    return supervisorSection("人工决策队列", [
      supervisorListItem("待处理决策", heading, openCount && openCount > 0 ? "blocked" : required.status, [
        required.status === "unavailable" ? "暂无人工决策数据" : "暂无待处理决策",
      ]),
    ]);
  }
  const list = el("div", "supervisor-list");
  decisions.slice(0, 6).forEach((decision) => {
    const details = [
      decision.reason ? `原因：${supervisorReasonLabel(decision.reason)}` : "",
      decision.failure_key ? `失败键：${decision.failure_key}` : "",
      decision.required_user_decision ? `需要用户决定：${userDecisionInstructionLabel(decision.required_user_decision)}` : "",
      decision.summary ? `摘要：${decision.summary}` : "",
      decision.opened_at ? `打开：${formatTime(decision.opened_at)}` : "",
    ].filter(Boolean);
    list.append(supervisorListItem(decision.decision_id || decision.failure_key || "人工决策", supervisorStatusLabel(decision.status || "open"), decision.status || "blocked", details));
  });
  return supervisorSection("人工决策队列", [list]);
}

function renderSupervisorConfig(bundle) {
  const snapshot = supervisorSnapshot(bundle);
  const services = bundle.services || {};
  const decisions = bundle.decisions || {};
  const rows = [
    ["模式", snapshot.mode ? text(snapshot.mode) : "未启用"],
    ["Watch 间隔", watchIntervalLabel(snapshot.watch_interval_seconds)],
    ["最近心跳", snapshot.last_heartbeat_at ? formatTime(snapshot.last_heartbeat_at) : "暂无数据"],
    ["最近 tick", snapshot.last_tick_at ? formatTime(snapshot.last_tick_at) : "暂无数据"],
    ["服务检查", services.checked_at ? formatTime(services.checked_at) : "暂无数据"],
    ["状态产物", text((bundle.summary || {}).artifact_path, "不可用")],
    ["决策计数", decisions.counts ? `决策=${numberText(decisions.counts.decisions_total)}，续跑计划=${numberText(decisions.counts.continuation_plans_total)}` : "暂无数据"],
  ];
  const grid = el("div", "supervisor-config-grid");
  rows.forEach(([label, value]) => grid.append(infoRow(label, value)));
  return supervisorSection("配置", [grid]);
}

function renderSupervisorDiagnostics(bundle) {
  const diagnostics = Object.values(bundle || {}).flatMap((payload) => arrayValue(payload && payload.diagnostics));
  if (!diagnostics.length) {
    return null;
  }
  const list = el("div", "supervisor-list");
  diagnostics.slice(0, 8).forEach((diagnostic) => {
    list.append(supervisorListItem(text(diagnostic.source, "诊断"), text(diagnostic.status, "不可用"), diagnostic.status, [
      text(diagnostic.message, "暂无数据"),
    ]));
  });
  return supervisorSection("Supervisor 诊断", [list]);
}

function supervisorSection(title, children) {
  const section = el("section", "supervisor-section");
  section.append(el("h2", "supervisor-section-title", title), ...children);
  return section;
}

function supervisorMetric(label, value, note) {
  const item = el("div", "supervisor-metric");
  item.append(
    el("span", "supervisor-metric-label", label),
    el("span", "supervisor-metric-value", text(value, "暂无数据")),
    el("span", "supervisor-metric-note", text(note, "暂无数据")),
  );
  return item;
}

function supervisorChip(label, status) {
  return el("span", `badge ${supervisorStatusClass(status)}`, text(label, "暂无数据"));
}

function supervisorListItem(title, badgeText, badgeStatus, details) {
  const item = el("article", "supervisor-list-item");
  const row = el("div", "supervisor-row");
  row.append(el("span", "supervisor-row-title", text(title, "暂无数据")), supervisorChip(badgeText, badgeStatus));
  item.append(row);
  const detailWrap = el("div", "supervisor-row-detail");
  const normalized = normalizeList(details);
  if (!normalized.length) {
    detailWrap.append(el("span", "supervisor-detail-chip", "暂无数据"));
  } else {
    normalized.forEach((detail) => detailWrap.append(el("span", "supervisor-detail-chip", detail)));
  }
  item.append(detailWrap);
  return item;
}

function supervisorSnapshot(bundle) {
  return objectValue(bundle && bundle.summary && bundle.summary.state);
}

function supervisorServices(bundle) {
  return arrayValue(bundle && bundle.services && bundle.services.services);
}

function supervisorDecisions(bundle) {
  return arrayValue(bundle && bundle.decisions && bundle.decisions.decisions);
}

function supervisorPlans(bundle) {
  return arrayValue(bundle && bundle.decisions && bundle.decisions.continuation_plans);
}

function supervisorAttempts(bundle) {
  return arrayValue(bundle && bundle.recovery && bundle.recovery.attempts);
}

function supervisorAudits(bundle) {
  return arrayValue(bundle && bundle.auditor && bundle.auditor.audits);
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function numberOrNull(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string" && !value.trim()) {
    return null;
  }
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function numberText(value) {
  const number = numberOrNull(value);
  return number === null ? "暂无数据" : String(number);
}

function openCountLabel(value) {
  const number = numberOrNull(value);
  if (number === null) {
    return "不可用";
  }
  return number > 0 ? `${number} 条待处理` : "暂无待处理";
}

function watchIntervalLabel(value) {
  const number = numberOrNull(value);
  return number === null || number <= 0 ? "不可用" : `${number}s`;
}

function supervisorDecisionAvailable(decision) {
  const normalized = objectValue(decision);
  return Boolean(
    text(normalized.action, "") ||
    text(normalized.classification, "") ||
    text(normalized.summary, ""),
  );
}

function currentSupervisorDecision(bundle) {
  const decisions = supervisorDecisions(bundle).filter(supervisorDecisionAvailable);
  if (decisions.length) {
    return decisions[0];
  }
  const snapshotDecision = objectValue(supervisorSnapshot(bundle).last_decision);
  return supervisorDecisionAvailable(snapshotDecision) ? snapshotDecision : null;
}

function supervisorDecisionStatus(decision) {
  return text(decision.action || decision.classification, "waiting");
}

function supervisorDecisionBadge(decision) {
  if (decision.action) {
    return supervisorActionLabel(decision.action);
  }
  if (decision.classification) {
    return supervisorClassificationLabel(decision.classification);
  }
  return "等待";
}

function supervisorDecisionDetail(decision) {
  const classification = decision.classification ? supervisorClassificationLabel(decision.classification) : "";
  return text(decision.summary || decision.reason || classification || decision.decision_id, "暂无最近决策");
}

function supervisorStatusLabel(status) {
  const normalized = text(status, "unavailable");
  return SUPERVISOR_STATUS_LABELS[normalized] || text(normalized, "不可用");
}

function supervisorActionLabel(action) {
  const normalized = text(action, "");
  return SUPERVISOR_ACTION_LABELS[normalized] || ACTION_LABELS[normalized] || "未识别动作";
}

function supervisorClassificationLabel(classification) {
  const normalized = text(classification, "");
  return SUPERVISOR_CLASSIFICATION_LABELS[normalized] || "未识别分类";
}

function supervisorReasonLabel(reason) {
  const normalized = text(reason, "");
  const labels = {
    retry_ceiling_exceeded: "同一问题连续恢复失败达到上限",
    auditor_stop: "Auditor 要求停止",
    unsafe_secret: "发现疑似敏感信息",
    unsupported_state: "运行状态暂不支持自动处理",
    human_merge_required: "需要人工合并确认",
    global_stop_open_user_decision: "存在待处理人工决策",
    active_demand_phase: "需求开发任务正在运行",
    audit_blocked: "审计阻塞等待整改",
    supported_stopped_blocked: "阻塞状态可恢复",
    terminal_no_action: "终态无需动作",
    autonomous_budget_stop: "自动资料拓展达到本轮预算",
  };
  return labels[normalized] || "需要人工判断";
}

function userDecisionInstructionLabel(instruction) {
  const normalized = text(instruction, "");
  const labels = {
    "Inspect the repeated recovery failure and choose the next action.": "检查连续恢复失败原因，并选择下一步处理方式。",
    "Review the auditor stop conclusion and choose whether to stop or continue manually.": "复核 Auditor 停止结论，并决定停止还是人工继续。",
    "Inspect artifacts for secrets before any automatic continuation.": "先检查产物中的敏感信息，再决定是否允许自动继续。",
    "Inspect the run state and choose the next operational action.": "检查运行状态，并选择下一步控制动作。",
  };
  return labels[normalized] || "请查看详情并选择下一步处理方式。";
}

function auditCadenceLabel(cadence) {
  if (!cadence || typeof cadence !== "object" || Array.isArray(cadence)) {
    return text(cadence, "暂无数据");
  }
  const parts = [
    cadence.current_interval !== undefined ? `当前间隔 ${cadence.current_interval}` : "",
    cadence.steps_since_last_audit !== undefined ? `已过 ${cadence.steps_since_last_audit}` : "",
    cadence.next_interval_after_verdict !== undefined ? `下次间隔 ${cadence.next_interval_after_verdict}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join("；") : "暂无数据";
}

function supervisorStatusClass(status) {
  const normalized = text(status, "unavailable").toLowerCase();
  if (["healthy", "available", "pass", "passed"].includes(normalized)) {
    return "status-done";
  }
  if (["degraded", "planned", "created", "observe", "continue", "refocus", "running", "pending", "active", "actionable_resume", "continuation_candidate", "resume", "restart_service", "create_continuation"].includes(normalized)) {
    return "status-running";
  }
  if (["blocked", "stopped", "stop", "fail", "failed", "invalid_artifact", "must_fix", "request_user_decision", "needs_user_decision", "unsupported", "open"].includes(normalized)) {
    return "status-blocked";
  }
  return "status-waiting";
}

function supervisorBoxStatusClass(status) {
  const badgeClass = supervisorStatusClass(status);
  if (badgeClass === "status-done") {
    return "is-done";
  }
  if (badgeClass === "status-running") {
    return "is-running";
  }
  if (badgeClass === "status-blocked") {
    return "is-blocked";
  }
  return "is-waiting";
}

function servicesStatus(services) {
  if (!services.length) {
    return "unavailable";
  }
  if (services.some((service) => ["blocked", "invalid_artifact"].includes(text(service.status, "")))) {
    return "blocked";
  }
  if (services.every((service) => text(service.status, "") === "healthy")) {
    return "healthy";
  }
  return "degraded";
}

function serviceNameLabel(service) {
  const labels = {
    "crawler-backend": "Crawler Backend",
    "crawler-frontend": "Crawler Frontend",
    "loop-dashboard": "Loop Dashboard",
    "loop-auto-resume": "loop-auto-resume",
  };
  return labels[service] || text(service, "未知服务");
}

function serviceReachableLabel(service) {
  if (service.reachable === true) {
    return "端点可达";
  }
  if (service.reachable === false) {
    return "端点不可达";
  }
  if (service.kind === "tmux") {
    return service.tmux_session_exists === true ? "tmux 存活" : service.tmux_session_exists === false ? "tmux 不存在" : "tmux 不可用";
  }
  return "端点不可用";
}

function serviceVersionLabel(service) {
  const version = objectValue(service.running_version);
  if (!Object.keys(version).length) {
    return { label: "版本不可用", status: "unavailable" };
  }
  if (version.freshness === "stale") {
    return { label: "版本过期", status: "degraded" };
  }
  if (version.matches_expected === true) {
    return { label: "版本匹配", status: "healthy" };
  }
  if (version.matches_expected === false) {
    return { label: "版本不匹配", status: "degraded" };
  }
  return { label: "版本不可用", status: "unavailable" };
}

function serviceBadgeStatus(service, version) {
  const serviceStatus = text(service.status, "");
  if (service.reachable === false || ["blocked", "invalid_artifact"].includes(serviceStatus)) {
    return "blocked";
  }
  if (serviceStatus === "degraded" || version.status === "degraded") {
    return "degraded";
  }
  return version.status;
}

function serviceTmuxEvidence(service) {
  if (!service.tmux_session) {
    return "tmux：未启用";
  }
  if (service.tmux_session_exists === true) {
    return `tmux：${service.tmux_session} 存活`;
  }
  if (service.tmux_session_exists === false) {
    return `tmux：${service.tmux_session} 不存在`;
  }
  return `tmux：${service.tmux_session} 状态不可用`;
}

function serviceEvidence(service) {
  const version = objectValue(service.running_version);
  const freshness = objectValue(service.data_freshness);
  return [
    service.expected_endpoint ? `端点：${service.expected_endpoint}` : "",
    serviceTmuxEvidence(service),
    version.runtime_metadata_path ? `runtime：${version.runtime_metadata_path}` : "runtime：不可用",
    version.git_head || version.origin_main ? `版本：git_head=${text(version.git_head, "不可用")} · origin=${text(version.origin_main, "不可用")}` : "",
    version.evidence ? `版本证据：${version.evidence}` : "",
    freshnessStatusLabel(freshness.status) !== "暂无 freshness target" ? `新鲜度：${freshnessStatusLabel(freshness.status)}` : "新鲜度：暂无 freshness target",
    freshness.target_id ? `target_id：${freshness.target_id}` : "",
    service.last_checked_at ? `检查：${formatTime(service.last_checked_at)}` : "",
    service.last_restart_at ? `最近重启：${formatTime(service.last_restart_at)}` : "",
    service.last_error ? `错误：${service.last_error}` : "",
  ].filter(Boolean);
}

function supervisorVersionSummary(services) {
  const versions = services.map((service) => objectValue(service.running_version)).filter((version) => Object.keys(version).length);
  if (!services.length) {
    return { value: "不可用", note: "暂无服务版本数据" };
  }
  if (!versions.length) {
    return { value: "不可用", note: "所有服务缺少 runtime metadata" };
  }
  const matched = versions.filter((version) => version.matches_expected === true).length;
  const unavailable = services.length - versions.length;
  const note = unavailable > 0 ? `${unavailable} 个服务缺少 runtime metadata` : "按 running_version.matches_expected 统计";
  return { value: `${matched} / ${services.length}`, note };
}

function supervisorFreshnessTargets(services) {
  return services.map((service) => {
    const freshness = objectValue(service.data_freshness);
    const checks = normalizeList(freshness.checks);
    return {
      service: service.service,
      status: freshness.status,
      target_id: freshness.target_id,
      checks,
      verified_at: freshness.verified_at,
    };
  }).filter((target) => target.status || target.target_id || target.checks.length);
}

function supervisorFreshnessSummary(services) {
  const targets = supervisorFreshnessTargets(services);
  if (!targets.length) {
    return { value: "暂无 freshness target", note: "暂无绑定 target、commit 或检查记录" };
  }
  const pass = targets.filter((target) => target.status === "pass").length;
  const fail = targets.filter((target) => target.status === "fail").length;
  const unavailable = targets.filter((target) => !target.status || target.status === "not_applicable").length;
  if (fail) {
    return { value: `${fail} 个失败`, note: targets.map((target) => target.target_id).filter(Boolean).join("；") || "查看服务行详情" };
  }
  if (pass) {
    return { value: `${pass} 个通过`, note: targets.map((target) => target.target_id).filter(Boolean).join("；") || "绑定服务新鲜度记录" };
  }
  return { value: "不可用", note: `${unavailable} 个 target 未启用或不适用` };
}

function freshnessStatusLabel(status) {
  const labels = {
    pass: "通过",
    fail: "失败",
    not_applicable: "不适用",
  };
  return labels[status] || "暂无 freshness target";
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
    const remediationSuffix = child.audit_remediation ? " · 审计整改" : "";
    card.append(
      el("div", "child-card-title", `${titlePrefix}${text(child.task_description || child.task_summary || child.run_id)}`),
      el("div", "child-card-meta", `${phaseLabel(child.phase)} · ${text(child.run_id)}${remediationSuffix}`),
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
  if (child.audit_remediation) {
    header.append(el("span", "status-pill status-running", "审计整改"));
  }
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
    ["引擎", text(summary.engine_status) === "active" ? "已接入" : "仅展示"],
    ["结论", auditVerdictLabel(summary.verdict)],
    ["open must_fix", String(Number(summary.open_must_fix) || 0)],
    ["方向控制", actionLabel(summary.direction_action)],
  ].forEach(([label, value]) => metrics.append(summaryMetric(label, value)));
  wrapper.append(metrics);

  const phaseNotice = text(summary.phase_notice, "");
  if (phaseNotice) {
    wrapper.append(el("div", "auditor-note auditor-phase-notice", phaseNotice));
  }

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
  title.append(el("span", "", "当前项目 Skill 使用情况"));
  wrapper.append(title);

  const metrics = el("div", "skill-metrics");
  [
    ["项目 Skill", String(Number(inventory.total_project_skills) || 0)],
    ["Loop 相关", String(Number(inventory.loop_related_skills) || 0)],
    [text(inventory.usage_label, "日志线索（非使用证明）"), String(Number(inventory.log_reference_count) || 0)],
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
