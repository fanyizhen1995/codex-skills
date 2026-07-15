(function () {
  "use strict";

  const { CursorPager, DashboardError } = window.LoopPagination;
  const {
    SupervisorView, renderTable, sectionHeading, metrics, node, text,
    readableValue, multiText, formatTime,
  } = window.LoopSupervisor;

  const RUN_TABS = ["overview", "children", "agents", "acceptance", "logs", "diagnostics", "artifacts"];
  const CHILD_STATUS_OPTIONS = [
    ["", "全部状态"],
    ["progressing", "进行中"], ["completed", "已完成"], ["blocked", "阻塞"],
    ["planned", "已计划"], ["generating", "生成中"], ["evaluating", "验收中"],
    ["repair_needed", "需要修复"], ["artifact_hygiene", "产物清理"], ["cleanup", "清理中"],
    ["passed", "通过"], ["stopped_budget", "停止：预算耗尽"],
    ["stopped_blocked", "停止：阻塞"], ["stopped_by_reviewer", "Reviewer 已停止"],
  ];
  const ACCEPTANCE_STATUS_OPTIONS = [
    ["", "全部状态"], ["pass", "通过"], ["passed", "通过"], ["fail", "失败"],
    ["failed", "失败"], ["blocked", "阻塞"], ["pending", "等待"], ["partial", "部分完成"],
  ];
  const DIAGNOSTIC_SEVERITIES = Object.freeze({
    critical: { label: "严重", tone: "bad" },
    error: { label: "错误", tone: "bad" },
    must_fix: { label: "必须修复", tone: "bad" },
    major: { label: "重要", tone: "warn" },
    warning: { label: "警告", tone: "warn" },
    should_fix: { label: "建议修复", tone: "warn" },
    minor: { label: "一般", tone: "neutral" },
    observe: { label: "观察", tone: "neutral" },
    info: { label: "信息", tone: "neutral" },
  });
  const DIAGNOSTIC_SEVERITY_OPTIONS = [
    ["", "全部严重性"],
    ...Object.entries(DIAGNOSTIC_SEVERITIES).map(([value, metadata]) => [value, metadata.label]),
  ];
  const state = {
    view: "supervisor",
    selectedRunId: "",
    detail: null,
    activeRunTab: "overview",
    activeRunPagerKey: "",
    runPagers: new Map(),
    runListPager: null,
    requestSequence: 0,
    detailAbortController: null,
    projectAbortController: null,
  };

  const els = {
    project: document.getElementById("project-status"),
    topStatus: document.getElementById("top-status"),
    refreshButton: document.getElementById("refresh-button"),
    supervisorNav: document.getElementById("supervisor-nav"),
    supervisorNavStatus: document.getElementById("supervisor-nav-status"),
    supervisorView: document.getElementById("supervisor-view"),
    supervisorPanel: document.getElementById("supervisor-panel-content"),
    supervisorHero: document.getElementById("supervisor-hero-status"),
    runList: document.getElementById("run-list"),
    runView: document.getElementById("run-view"),
    runTitle: document.getElementById("run-title"),
    runSubtitle: document.getElementById("run-subtitle"),
    runHero: document.getElementById("run-hero-status"),
    runOverview: document.getElementById("run-overview"),
    runToolbar: document.getElementById("run-toolbar"),
    runPanel: document.getElementById("run-panel-content"),
  };

  const supervisor = new SupervisorView({
    panel: els.supervisorPanel,
    hero: els.supervisorHero,
    topStatus: els.topStatus,
    navStatus: els.supervisorNavStatus,
    fetchJson,
  });

  async function fetchJson(path, options = {}) {
    const response = await fetch(path, { signal: options.signal });
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new DashboardError("invalid_json", `HTTP ${response.status}: 响应不是 JSON`, {
        httpStatus: response.status,
      });
    }
    if (payload && payload.status && payload.error) {
      const code = payload.error.code || payload.status || "request_failed";
      const message = payload.error.message || "数据不可用";
      const recoveryAction = payload.error.recovery_action || payload.recovery_action || "";
      throw new DashboardError(code, message, { recoveryAction, httpStatus: response.status, payload });
    }
    if (!response.ok) {
      const detail = payload && payload.detail;
      const message = typeof detail === "string" ? detail : detail?.message || `HTTP ${response.status}`;
      throw new DashboardError(`http_${response.status}`, message, { httpStatus: response.status, payload });
    }
    return payload;
  }

  async function boot() {
    bindNavigation();
    restoreViewState();
    syncView();
    syncRunTabs();
    await Promise.all([loadProject(), loadRunList()]);
    if (state.view === "run" && state.selectedRunId) await loadSelectedRun(state.selectedRunId);
    else await supervisor.show();
  }

  function bindNavigation() {
    els.supervisorNav.addEventListener("click", showSupervisor);
    els.refreshButton.addEventListener("click", refreshActiveView);
    const runTabs = Array.from(document.querySelectorAll("[data-run-tab]"));
    runTabs.forEach((button) => button.addEventListener("click", () => selectRunTab(button.dataset.runTab)));
    bindTabKeyboard(runTabs, (button) => selectRunTab(button.dataset.runTab));
  }

  function bindTabKeyboard(buttons, activate) {
    buttons.forEach((button, index) => {
      button.addEventListener("keydown", (event) => {
        let targetIndex = -1;
        if (event.key === "ArrowRight") targetIndex = (index + 1) % buttons.length;
        if (event.key === "ArrowLeft") targetIndex = (index - 1 + buttons.length) % buttons.length;
        if (event.key === "Home") targetIndex = 0;
        if (event.key === "End") targetIndex = buttons.length - 1;
        if (targetIndex < 0) return;
        event.preventDefault();
        buttons[targetIndex].focus();
        activate(buttons[targetIndex]);
      });
    });
  }

  function restoreViewState() {
    const url = new URL(window.location.href);
    const runId = url.searchParams.get("run_id") || "";
    const requestedRunTab = url.searchParams.get("run_tab") || "overview";
    state.selectedRunId = runId;
    state.view = runId ? "run" : "supervisor";
    state.activeRunTab = RUN_TABS.includes(requestedRunTab) ? requestedRunTab : "overview";
    canonicalizeViewUrl(url, requestedRunTab);
  }

  function canonicalizeViewUrl(url, requestedRunTab) {
    if (!state.selectedRunId) url.searchParams.delete("run_tab");
    else if (requestedRunTab !== state.activeRunTab) url.searchParams.set("run_tab", state.activeRunTab);
    window.history.replaceState({}, "", url);
  }

  async function loadProject() {
    if (state.projectAbortController) state.projectAbortController.abort();
    state.projectAbortController = new AbortController();
    try {
      const project = await fetchJson("/api/projects/current", { signal: state.projectAbortController.signal });
      const root = text(project.project_root, "不可用");
      const runRoot = text(project.run_root || project.runs_root, ".codex/loop-runs");
      els.project.textContent = `项目：${root} · 运行库：${runRoot} · 最近同步：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
    } catch (error) {
      if (error.name !== "AbortError") els.project.textContent = `项目状态不可用：${errorText(error)}`;
    }
  }

  async function loadRunList() {
    if (state.runListPager) return state.runListPager.refresh();
    const host = node("div", "pager-host");
    els.runList.replaceChildren(host);
    state.runListPager = new CursorPager({
      key: "run-list",
      endpoint: "/api/runs",
      container: host,
      allowedFilters: ["phase", "policy"],
      fixedSort: "newest",
      emptyMessage: "暂无运行记录",
      renderItems: (target, items) => renderRunButtons(target, items),
    });
    return state.runListPager.load();
  }

  function renderRunButtons(target, runs) {
    const list = node("div", "run-list-items");
    runs.forEach((run) => {
      const button = node("button", "nav-item run-button");
      button.type = "button";
      button.dataset.runId = text(run.run_id, "");
      button.classList.toggle("is-active", button.dataset.runId === state.selectedRunId);
      const title = node("span", "nav-title");
      title.append(
        node("span", "", text(run.run_id)),
        node("span", `status-text ${phaseTone(run.phase)}`, phaseLabel(run.phase)),
      );
      button.append(
        title,
        node("span", "nav-meta full-text", text(run.task_description || run.task_summary, "暂无任务说明")),
        node("span", "nav-meta", `${policyLabel(run.policy)} · ${formatTime(run.updated_at)}`),
      );
      button.addEventListener("click", () => selectRun(button.dataset.runId));
      list.append(button);
    });
    target.append(list);
  }

  async function showSupervisor() {
    abortRunRequests();
    state.view = "supervisor";
    state.selectedRunId = "";
    const url = new URL(window.location.href);
    url.searchParams.delete("run_id");
    url.searchParams.delete("run_tab");
    window.history.replaceState({}, "", url);
    syncView();
    await supervisor.show();
  }

  async function selectRun(runId) {
    if (!runId) return;
    supervisor.deactivate();
    state.view = "run";
    state.selectedRunId = runId;
    state.activeRunTab = "overview";
    const url = new URL(window.location.href);
    url.searchParams.set("run_id", runId);
    url.searchParams.set("run_tab", "overview");
    window.history.replaceState({}, "", url);
    syncView();
    syncRunTabs();
    await loadSelectedRun(runId);
  }

  function abortRunRequests() {
    state.requestSequence += 1;
    if (state.detailAbortController) state.detailAbortController.abort();
    if (state.activeRunPagerKey) state.runPagers.get(state.activeRunPagerKey)?.destroy();
    state.activeRunPagerKey = "";
  }

  async function loadSelectedRun(runId, options = {}) {
    const request = ++state.requestSequence;
    if (state.detailAbortController) state.detailAbortController.abort();
    state.detailAbortController = new AbortController();
    if (!state.detail || state.detail.run_id !== runId) {
      els.runPanel.replaceChildren(message("正在读取运行详情...", "empty-state"));
      els.runToolbar.replaceChildren();
    }
    try {
      const detail = await fetchJson(`/api/runs/${encodeURIComponent(runId)}`, {
        signal: state.detailAbortController.signal,
      });
      if (request !== state.requestSequence || runId !== state.selectedRunId) return;
      state.detail = detail;
      renderRunHeader(detail);
      renderRunSummary(detail);
      syncRunTabs();
      await loadActiveRunTab({ refresh: options.refresh === true });
    } catch (error) {
      if (error.name === "AbortError" || request !== state.requestSequence) return;
      state.detail = null;
      els.runPanel.replaceChildren(message(errorText(error), "error-state"));
    }
  }

  async function selectRunTab(tab) {
    if (!RUN_TABS.includes(tab) || !state.selectedRunId) return;
    const previousKey = state.activeRunPagerKey;
    state.activeRunTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set("run_tab", tab);
    window.history.replaceState({}, "", url);
    if (previousKey) state.runPagers.get(previousKey)?.destroy();
    state.activeRunPagerKey = "";
    syncRunTabs();
    await loadActiveRunTab();
  }

  async function loadActiveRunTab(options = {}) {
    if (!state.detail) return;
    els.runToolbar.replaceChildren();
    if (state.activeRunTab === "agents") {
      state.activeRunPagerKey = "";
      renderAgentResults();
      return;
    }
    const configs = runTabConfigs();
    const config = configs[state.activeRunTab];
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading(config.title, config.note));
    if (config.prelude) wrapper.append(config.prelude());
    const toolbar = buildRunToolbar(config);
    if (toolbar) wrapper.append(toolbar);
    const host = node("div", "pager-host");
    wrapper.append(host);
    els.runPanel.replaceChildren(wrapper);
    const pager = runPager(config, host);
    state.activeRunPagerKey = pager.key;
    hydrateRunToolbar(pager, config);
    if (options.refresh && pager.page) await pager.refresh();
    else await pager.load();
  }

  function runTabConfigs() {
    return {
      overview: {
        endpoint: "events", title: "运行事件", note: "事件按服务端快照稳定分页",
        filters: ["kind"], query: true, empty: "暂无运行事件", render: renderEvents,
        prelude: () => renderDecisionSummary(state.detail.decision_summary),
      },
      children: {
        endpoint: "children", title: "子任务", note: "完整展示每个子任务和 Agent 结果",
        filters: ["status"], filterOptions: CHILD_STATUS_OPTIONS, empty: "暂无子任务", render: renderChildren,
      },
      acceptance: {
        endpoint: "acceptance", title: "验收", note: "模拟用户验收与 Evaluator 结论",
        filters: ["status"], filterOptions: ACCEPTANCE_STATUS_OPTIONS, empty: "暂无结构化验收场景", render: renderAcceptance,
        prelude: () => renderAcceptanceEvidence(state.detail.acceptance_summary),
      },
      logs: {
        endpoint: "logs", title: "日志", note: "列表只含元数据；展开后读取有界详情",
        filters: ["stream"], query: true, empty: "暂无日志", render: renderLogs,
      },
      diagnostics: {
        endpoint: "diagnostics", title: "阻塞诊断", note: "完整展示 finding、严重性和来源",
        filters: ["kind", "severity"], empty: "暂无阻塞诊断", render: renderDiagnostics,
      },
      artifacts: {
        endpoint: "artifacts", title: "产物", note: "展示后端确认的标签、路径和更新时间",
        filters: [], query: true, empty: "暂无产物路径", render: renderArtifacts,
      },
    };
  }

  function runPager(config, host) {
    const key = `run-${state.selectedRunId}-${state.activeRunTab}`;
    const existing = state.runPagers.get(key);
    if (existing) {
      existing.container = host;
      existing.renderItems = config.render;
      return existing;
    }
    const pager = new CursorPager({
      key,
      endpoint: `/api/runs/${encodeURIComponent(state.selectedRunId)}/${config.endpoint}`,
      container: host,
      allowedFilters: config.filters,
      fixedSort: "newest",
      emptyMessage: config.empty,
      renderItems: config.render,
    });
    state.runPagers.set(key, pager);
    return pager;
  }

  function buildRunToolbar(config) {
    if (!config.filters.length && !config.query) return null;
    const toolbar = node("div", "toolbar run-filters");
    if (config.filters.includes("kind")) toolbar.append(selectFilter("kind", "类型", [["", "全部类型"], ["transition", "状态变化"], ["agent", "Agent"], ["skill", "Skill"], ["tool", "工具"]]));
    if (config.filters.includes("status")) toolbar.append(selectFilter("status", "状态", config.filterOptions || ACCEPTANCE_STATUS_OPTIONS));
    if (config.filters.includes("stream")) toolbar.append(selectFilter("stream", "日志流", [["", "全部日志"], ["stdout", "stdout"], ["stderr", "stderr"]]));
    if (config.filters.includes("severity")) toolbar.append(selectFilter("severity", "严重性", DIAGNOSTIC_SEVERITY_OPTIONS));
    if (config.query) {
      const label = node("label", "filter-control");
      const input = node("input", "control");
      input.type = "search";
      input.dataset.query = "true";
      input.placeholder = "输入关键词";
      input.setAttribute("aria-label", "关键词");
      label.append(node("span", "", "关键词"), input);
      toolbar.append(label);
    }
    return toolbar;
  }

  function selectFilter(name, labelText, options) {
    const label = node("label", "filter-control");
    const select = node("select", "control");
    select.dataset.filter = name;
    select.setAttribute("aria-label", labelText);
    options.forEach(([value, optionLabel]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = optionLabel;
      select.append(option);
    });
    label.append(node("span", "", labelText), select);
    return label;
  }

  function hydrateRunToolbar(pager, config) {
    els.runPanel.querySelectorAll("[data-filter]").forEach((control) => {
      control.value = pager.state.filters[control.dataset.filter] || "";
      control.addEventListener("change", async () => {
        await pager.setFilter(control.dataset.filter, control.value);
        control.value = pager.state.filters[control.dataset.filter] || "";
      });
    });
    const query = els.runPanel.querySelector("[data-query]");
    if (query && config.query) {
      query.value = pager.state.query;
      query.addEventListener("change", async () => {
        await pager.setQuery(query.value);
        query.value = pager.state.query;
      });
    }
  }

  function renderRunHeader(detail) {
    els.runTitle.textContent = text(detail.run_id, "运行详情");
    els.runSubtitle.textContent = text(detail.task_description || detail.task_summary, "暂无任务说明");
    els.runHero.replaceChildren(node("span", `status-chip ${phaseTone(detail.phase)}`, phaseLabel(detail.phase)));
    els.topStatus.replaceChildren(
      node("span", `status-chip ${phaseTone(detail.phase)}`, `运行${phaseLabel(detail.phase)}`),
      node("span", "status-chip neutral", "只读运行详情"),
    );
  }

  function renderRunSummary(detail) {
    const reader = objectValue(detail.reader_summary);
    const attempts = objectValue(detail.attempts);
    const content = metrics([
      ["当前阶段", phaseLabel(detail.phase)],
      ["下一动作", actionLabel(detail.next_action)],
      ["最近结果", resultLabel(detail.last_result)],
      ["Agent 尝试", `${numberText(attempts.planner)} / ${numberText(attempts.generator)} / ${numberText(attempts.evaluator)}`],
    ]);
    const purpose = node("div", "run-purpose full-text");
    purpose.append(
      node("strong", "", "任务目标"),
      node("div", "", text(detail.task_description || detail.task_summary, "暂无任务说明")),
      node("div", "cell-detail", `当前进展：${text(reader.current_progress, "暂无数据")}`),
      node("div", "cell-detail", `下一步：${text(reader.next_step, "暂无数据")}`),
      node("div", "cell-detail", `策略：${policyLabel(detail.policy)} · 来源：${text(detail.source_path, "不可用")}`),
    );
    els.runOverview.replaceChildren(content, purpose);
  }

  function renderDecisionSummary(value) {
    const decision = objectValue(value);
    const wrapper = node("div", "decision-summary");
    wrapper.append(
      node("strong", "", "运行决策"),
      node("div", "full-text", text(decision.decision_label, "暂无决策")),
      node("div", "cell-detail full-text", `原因：${text(decision.reason, "暂无数据")}`),
      node("div", "cell-detail", `下一动作：${actionLabel(decision.next_action)} · 需要用户：${booleanLabel(decision.requires_user_decision)}`),
    );
    return wrapper;
  }

  function renderEvents(target, items) {
    renderTable(target, ["时间", "类型", "事件", "来源"], items.map((item) => [
      formatTime(item.updated_at || item.timestamp),
      eventKindLabel(item.kind || item.event_type),
      multiText(item.message || item.summary, readableValue(item.details, "")),
      text(item.source, "不可用"),
    ]));
  }

  function renderChildren(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const reader = objectValue(item.reader_summary);
      const decision = objectValue(item.decision_summary);
      const child = node("article", "list-item child-detail");
      const heading = node("div", "list-row");
      heading.append(
        node("strong", "full-text", text(item.task_description || item.task_summary || item.run_id)),
        node("span", `status-text ${phaseTone(item.phase)}`, phaseLabel(item.phase)),
      );
      child.append(
        heading,
        node("div", "cell-detail full-text", `运行：${text(item.run_id)} · 序号：${numberText(item.child_index)}`),
        node("div", "cell-detail full-text", `目标：${text(reader.purpose || item.task_description, "暂无")}`),
        node("div", "cell-detail full-text", `决策：${text(decision.decision_label, "暂无")}；${text(decision.reason, "暂无原因")}`),
        renderChildAgents(item.agents),
        labeledValues("子任务产物", item.artifact_paths, "暂无产物"),
      );
      list.append(child);
    });
    target.append(list);
  }

  function renderChildAgents(value) {
    const wrapper = node("div", "child-agent-grid");
    const agents = objectValue(value);
    ["planner", "generator", "evaluator"].forEach((name) => {
      wrapper.append(renderAgentPayload(name, objectValue(agents[name]), true));
    });
    return wrapper;
  }

  function renderAgentResults() {
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading("Agent 结果", "Planner、Generator 和 Evaluator 的完整状态、尝试、结论和产物"));
    const agents = node("div", "agent-grid");
    const values = objectValue(state.detail?.agents);
    ["planner", "generator", "evaluator"].forEach((name) => {
      agents.append(renderAgentPayload(name, objectValue(values[name]), false));
    });
    wrapper.append(agents);
    els.runPanel.replaceChildren(wrapper);
  }

  function renderAgentPayload(name, payload, compact) {
    const item = node("article", compact ? "agent-result compact" : "agent-result");
    item.append(
      node("strong", "", agentName(name)),
      node("div", `status-text ${agentStatusTone(payload.status)}`, agentStatusLabel(payload.status)),
      node("div", "cell-detail", `尝试：${numberText(payload.attempt)}`),
      node("div", "cell-detail full-text", `当前动作：${actionLabel(payload.current_action)}`),
      node("div", "full-text", `最近结果：${text(payload.last_result, "暂无结果")}`),
      labeledValues("产物", payload.artifact_paths, "暂无产物"),
    );
    return item;
  }

  function renderAcceptanceEvidence(value) {
    const acceptance = objectValue(value);
    const wrapper = node("div", "acceptance-evidence");
    wrapper.append(
      node("div", `status-text ${acceptanceTone(acceptance.status)}`, `总体状态：${acceptanceLabel(acceptance.status)}`),
      labeledValues("已检查", acceptance.checked, "暂无检查项"),
      labeledValues("验收证据", acceptance.evidence, "暂无证据"),
      labeledValues("复验命令", acceptance.rerun_commands, "暂无复验命令", "code-list"),
    );
    return wrapper;
  }

  function renderAcceptance(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const row = node("article", "list-item");
      row.append(
        node("strong", "full-text", text(item.scenario_id || item.title || item.name, "验收场景")),
        node("div", `status-text ${acceptanceTone(item.status)}`, acceptanceLabel(item.status)),
        node("div", "cell-detail full-text", text(item.summary, "暂无验收说明")),
      );
      list.append(row);
    });
    target.append(list);
  }

  function renderLogs(target, items) {
    const list = node("div", "log-list");
    items.forEach((item, index) => {
      const row = node("article", "log-row");
      const heading = node("div", "list-row");
      heading.append(
        node("strong", "full-text", text(item.source || item.log_id, "日志")),
        node("span", "status-text", text(item.stream, "日志")),
      );
      const detailId = `log-detail-${safeDomId(item.log_id || String(index))}`;
      const button = node("button", "link-button", "展开日志详情");
      button.type = "button";
      button.dataset.logDetail = item.log_id;
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-controls", detailId);
      const detail = node("pre", "log-detail");
      detail.id = detailId;
      detail.dataset.logDetailPanel = item.log_id;
      detail.hidden = true;
      button.addEventListener("click", () => expandLogDetail(item.log_id, button, detail));
      row.append(
        heading,
        node("div", "cell-detail full-text", text(item.summary, "列表未提供内容摘要")),
        node("div", "cell-detail", `${numberText(item.total_bytes)} bytes · 尝试 ${text(item.attempt_id, "不可用")} · ${formatTime(item.updated_at)}`),
        button,
        detail,
      );
      list.append(row);
    });
    target.append(list);
  }

  async function expandLogDetail(logId, button, detailPanel) {
    if (!logId || button.dataset.loaded === "true") {
      detailPanel.hidden = !detailPanel.hidden;
      button.setAttribute("aria-expanded", String(!detailPanel.hidden));
      button.textContent = detailPanel.hidden ? "展开日志详情" : "收起日志详情";
      return;
    }
    button.disabled = true;
    button.textContent = "正在读取...";
    try {
      const runId = state.selectedRunId;
      const detail = await fetchJson(`/api/runs/${encodeURIComponent(runId)}/logs/${encodeURIComponent(logId)}`);
      if (runId !== state.selectedRunId) return;
      detailPanel.textContent = text(detail.content, "日志内容为空");
      detailPanel.hidden = false;
      button.dataset.loaded = "true";
      button.setAttribute("aria-expanded", "true");
      button.textContent = detail.truncated ? "收起日志详情（内容已截断）" : "收起日志详情";
    } catch (error) {
      detailPanel.textContent = errorText(error);
      detailPanel.hidden = false;
      button.setAttribute("aria-expanded", "true");
      button.textContent = "重试日志详情";
    } finally {
      button.disabled = false;
    }
  }

  function renderDiagnostics(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const row = node("article", `list-item severity-${severityTone(item.severity)}`);
      row.append(
        node("strong", "full-text", text(item.title || item.kind, "诊断")),
        node("div", `status-text ${severityTone(item.severity)}`, severityLabel(item.severity)),
        node("div", "full-text", text(item.message || item.summary, "暂无诊断说明")),
        labeledValues("证据", item.evidence, "暂无证据"),
        node("div", "cell-detail full-text", `来源：${text(item.source, "不可用")}`),
      );
      list.append(row);
    });
    target.append(list);
  }

  function renderArtifacts(target, items) {
    renderTable(target, ["标签", "路径", "更新时间"], items.map((item) => [
      text(item.label, "未命名产物"),
      node("span", "full-text artifact-path", text(item.path, "不可用")),
      formatTime(item.updated_at),
    ]));
  }

  async function refreshActiveView() {
    if (els.refreshButton.disabled) return;
    els.refreshButton.disabled = true;
    els.refreshButton.textContent = "刷新中";
    try {
      await loadProject();
      await state.runListPager?.refresh();
      if (state.view === "supervisor") await supervisor.refresh();
      else if (state.selectedRunId) await loadSelectedRun(state.selectedRunId, { refresh: true });
    } finally {
      els.refreshButton.disabled = false;
      els.refreshButton.textContent = "刷新";
    }
  }

  function syncView() {
    const supervisorActive = state.view === "supervisor";
    els.supervisorView.classList.toggle("is-hidden", !supervisorActive);
    els.runView.classList.toggle("is-hidden", supervisorActive);
    els.supervisorNav.classList.toggle("is-active", supervisorActive);
    document.querySelectorAll(".run-button").forEach((button) => {
      button.classList.toggle("is-active", !supervisorActive && button.dataset.runId === state.selectedRunId);
    });
  }

  function syncRunTabs() {
    document.querySelectorAll("[data-run-tab]").forEach((button) => {
      const selected = button.dataset.runTab === state.activeRunTab;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-selected", String(selected));
      button.setAttribute("tabindex", selected ? "0" : "-1");
      if (selected) els.runPanel.setAttribute("aria-labelledby", button.id);
    });
  }

  function labeledValues(label, value, fallback, className = "value-list") {
    const wrapper = node("div", className);
    wrapper.append(node("strong", "value-label", label));
    const values = Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && item !== "") : [];
    if (!values.length) wrapper.append(node("span", "cell-detail", fallback));
    else values.forEach((item) => wrapper.append(node("div", "full-text", readableValue(item, fallback))));
    return wrapper;
  }

  function objectValue(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function numberText(value) {
    return Number.isFinite(Number(value)) ? String(Number(value)) : "不可用";
  }

  function booleanLabel(value) {
    if (value === true) return "是";
    if (value === false) return "否";
    return "不可用";
  }

  function errorText(error) {
    if (error instanceof DashboardError) {
      return error.recoveryAction
        ? `${error.code}：${error.message}；建议：${error.recoveryAction}`
        : `${error.code}：${error.message}`;
    }
    return error?.message || "请求失败";
  }

  function safeDomId(value) {
    return String(value || "log").replace(/[^A-Za-z0-9_-]/g, "-");
  }

  function phaseLabel(value) {
    const labels = {
      preflight: "预检中", planned: "已计划", generating: "生成中", verifying: "证据验证中",
      evaluating: "验收中", repair_needed: "需要修复", artifact_hygiene: "产物清理中",
      cleanup: "清理中", passed_waiting_human_merge: "通过，等待人工合并", planning: "规划中",
      committed: "已提交", stopped_no_action: "停止：无需操作", stopped_by_reviewer: "Reviewer 已停止",
      stopped_budget: "停止：预算耗尽", stopped_blocked: "停止：阻塞", audit_pending: "历史审视待处理",
      auditing: "历史审视中", audit_passed: "历史审视通过", audit_blocked: "历史审视阻塞",
      child_running: "子任务运行中", passed: "通过", invalid_artifact: "产物无效", terminal: "已终止",
    };
    return labels[value] || "阶段不可用";
  }

  function phaseTone(value) {
    if (["passed", "passed_waiting_human_merge", "stopped_no_action", "audit_passed", "committed"].includes(value)) return "good";
    if (["stopped_blocked", "stopped_by_reviewer", "invalid_artifact", "audit_blocked", "terminal"].includes(value)) return "bad";
    if ([
      "preflight", "planned", "child_running", "planning", "generating", "verifying", "evaluating",
      "repair_needed", "artifact_hygiene", "cleanup", "stopped_budget", "audit_pending", "auditing",
    ].includes(value)) return "warn";
    return "neutral";
  }

  function agentStatusLabel(value) {
    const labels = {
      done: "完成", implemented: "已实现", repaired: "已修复", passed: "通过", pass: "通过", ready: "就绪",
      running: "运行中", waiting: "等待", blocked: "阻塞", skipped: "跳过", fail: "失败", failed: "失败",
      timeout: "超时", invalid_json: "结果格式无效", missing: "暂无产物",
    };
    return labels[value] || "状态不可用";
  }

  function agentStatusTone(value) {
    if (["done", "implemented", "repaired", "passed", "pass", "ready"].includes(value)) return "good";
    if (["blocked", "fail", "failed", "timeout", "invalid_json", "missing"].includes(value)) return "bad";
    if (["running", "waiting", "skipped"].includes(value)) return "warn";
    return "neutral";
  }

  function acceptanceLabel(value) {
    const labels = {
      pass: "通过", passed: "通过", partial: "部分完成", pending: "等待验收",
      fail: "失败", failed: "失败", blocked: "阻塞", missing: "暂无验收数据", ready: "待验收",
    };
    return labels[value] || "验收状态不可用";
  }

  function acceptanceTone(value) {
    if (["pass", "passed"].includes(value)) return "good";
    if (["fail", "failed", "blocked", "missing"].includes(value)) return "bad";
    if (["partial", "pending", "ready"].includes(value)) return "warn";
    return "neutral";
  }

  function severityLabel(value) {
    return DIAGNOSTIC_SEVERITIES[value]?.label || "严重性不可用";
  }

  function severityTone(value) {
    return DIAGNOSTIC_SEVERITIES[value]?.tone || "neutral";
  }

  function actionLabel(value) {
    if (!value) return "暂无动作";
    const labels = {
      run_parent_planner: "运行父 Planner", run_child_planner: "运行子任务 Planner",
      run_planner: "运行 Planner", run_generator: "运行 Generator", run_child_generator: "运行子任务 Generator",
      run_evaluator: "运行 Evaluator", return_to_parent_planner: "返回父 Planner",
      repair_child: "修复子任务", recover_generator_result: "恢复 Generator 结果",
      repair_from_evaluator_findings: "按 Evaluator finding 修复", repair_and_reevaluate: "修复后重新验收",
      await_human_merge_confirmation: "等待人工合并确认", none: "暂无动作",
    };
    return labels[value] || "动作不可用";
  }

  function resultLabel(value) {
    const labels = { pass: "通过", passed: "通过", none: "暂无结果", blocked: "阻塞", fail: "失败", failed: "失败", budget_exhausted: "预算耗尽" };
    return labels[value] || "结果不可用";
  }

  function policyLabel(value) {
    return { demand_development: "需求开发", autonomous_knowledge: "自主知识拓展" }[value] || "策略不可用";
  }

  function agentName(value) {
    return { planner: "Planner", generator: "Generator", evaluator: "Evaluator" }[value] || "未知 Agent";
  }

  function eventKindLabel(value) {
    return { transition: "状态变化", agent: "Agent", skill: "Skill", tool: "工具", log: "日志" }[value] || "未分类";
  }

  function message(value, className) {
    return node("div", className, value);
  }

  boot().catch((error) => {
    els.topStatus.replaceChildren(message(`初始化失败：${errorText(error)}`, "error-state"));
  });
}());
