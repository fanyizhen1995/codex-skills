(function () {
  "use strict";

  const { CursorPager } = window.LoopPagination;
  const {
    SupervisorView, renderTable, section, sectionHeading, metrics, node, text,
    readableValue, statusText, multiText, formatTime,
  } = window.LoopSupervisor;

  const RUN_TABS = ["overview", "children", "agents", "acceptance", "logs", "diagnostics", "artifacts"];
  const state = {
    view: "supervisor",
    selectedRunId: "",
    detail: null,
    activeRunTab: "overview",
    runPagers: new Map(),
    runListPager: null,
    requestSequence: 0,
  };

  const els = {
    project: document.getElementById("project-status"),
    topStatus: document.getElementById("top-status"),
    supervisorNav: document.getElementById("supervisor-nav"),
    supervisorNavStatus: document.getElementById("supervisor-nav-status"),
    supervisorView: document.getElementById("supervisor-view"),
    supervisorPanel: document.getElementById("supervisor-panel-content"),
    supervisorHero: document.getElementById("supervisor-hero-status"),
    runList: document.getElementById("run-list"),
    runListPager: document.getElementById("run-list-pager"),
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

  async function fetchJson(path) {
    const response = await fetch(path);
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error(`HTTP ${response.status}: 响应不是 JSON`);
    }
    if (!response.ok) {
      const detail = payload.detail || payload.error?.message || payload.status || "请求失败";
      throw new Error(`HTTP ${response.status}: ${detail}`);
    }
    if (payload && payload.status && payload.error) {
      const code = payload.error.code || payload.status;
      const message = payload.error.message || "数据不可用";
      throw new Error(`${code}: ${message}`);
    }
    return payload;
  }

  async function boot() {
    bindNavigation();
    restoreViewState();
    await Promise.all([loadProject(), loadRunList()]);
    if (state.view === "run" && state.selectedRunId) await loadSelectedRun(state.selectedRunId);
    else await showSupervisor();
  }

  function bindNavigation() {
    els.supervisorNav.addEventListener("click", showSupervisor);
    document.querySelectorAll("[data-run-tab]").forEach((button) => {
      button.addEventListener("click", () => selectRunTab(button.dataset.runTab));
    });
  }

  function restoreViewState() {
    const params = new URL(window.location.href).searchParams;
    const runId = params.get("run_id") || "";
    const runTab = params.get("run_tab") || "overview";
    state.selectedRunId = runId;
    state.view = runId ? "run" : "supervisor";
    state.activeRunTab = RUN_TABS.includes(runTab) ? runTab : "overview";
  }

  async function loadProject() {
    try {
      const project = await fetchJson("/api/projects/current");
      const root = text(project.project_root, "不可用");
      const runRoot = text(project.run_root || project.runs_root, ".codex/loop-runs");
      els.project.textContent = `项目：${root} · 运行库：${runRoot} · 最近同步：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
    } catch (error) {
      els.project.textContent = `项目状态不可用：${error.message}`;
    }
  }

  async function loadRunList() {
    const host = node("div", "pager-host");
    els.runList.replaceChildren(host);
    state.runListPager = new CursorPager({
      key: "run-list",
      endpoint: "/api/runs",
      container: host,
      allowedFilters: ["phase", "policy"],
      emptyMessage: "暂无运行记录",
      renderItems: (target, items) => renderRunButtons(target, items),
    });
    await state.runListPager.load();
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
        node("span", "status-text warn", phaseLabel(run.phase || run.status)),
      );
      button.append(
        title,
        node("span", "nav-meta full-text", runSummary(run)),
        node("span", "nav-meta", `${policyLabel(run.policy)} · ${formatTime(run.updated_at || run.created_at)}`),
      );
      button.addEventListener("click", () => selectRun(button.dataset.runId));
      list.append(button);
    });
    target.append(list);
  }

  async function showSupervisor() {
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
    state.view = "run";
    state.selectedRunId = runId;
    state.activeRunTab = "overview";
    const url = new URL(window.location.href);
    url.searchParams.set("run_id", runId);
    url.searchParams.set("run_tab", "overview");
    window.history.replaceState({}, "", url);
    syncView();
    await loadSelectedRun(runId);
  }

  async function loadSelectedRun(runId) {
    const request = ++state.requestSequence;
    els.runPanel.replaceChildren(message("正在读取运行详情...", "empty-state"));
    els.runToolbar.replaceChildren();
    try {
      const detail = await fetchJson(`/api/runs/${encodeURIComponent(runId)}`);
      if (request !== state.requestSequence || runId !== state.selectedRunId) return;
      state.detail = detail;
      renderRunHeader(detail);
      renderRunSummary(detail);
      syncRunTabs();
      await loadActiveRunTab();
    } catch (error) {
      if (request !== state.requestSequence) return;
      state.detail = null;
      els.runPanel.replaceChildren(message(error.message || "运行详情不可用", "error-state"));
    }
  }

  async function selectRunTab(tab) {
    if (!RUN_TABS.includes(tab) || !state.selectedRunId) return;
    state.activeRunTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set("run_tab", tab);
    window.history.replaceState({}, "", url);
    syncRunTabs();
    await loadActiveRunTab();
  }

  async function loadActiveRunTab() {
    if (!state.detail) return;
    els.runToolbar.replaceChildren();
    if (state.activeRunTab === "agents") {
      renderAgentResults();
      return;
    }
    const configs = {
      overview: {
        endpoint: "events", title: "运行事件", note: "事件按服务端快照稳定分页",
        filters: ["kind"], query: true, empty: "暂无运行事件", render: renderEvents,
      },
      children: {
        endpoint: "children", title: "子任务", note: "完整展示任务和 Agent 结果",
        filters: ["status"], empty: "暂无子任务", render: renderChildren,
      },
      acceptance: {
        endpoint: "acceptance", title: "验收", note: "模拟用户验收与 Evaluator 结论",
        filters: ["status"], empty: "暂无结构化验收场景", render: renderAcceptance,
      },
      logs: {
        endpoint: "logs", title: "日志", note: "列表只含元数据；展开后读取有界详情",
        filters: ["stream"], query: true, empty: "暂无日志", render: renderLogs,
      },
      diagnostics: {
        endpoint: "diagnostics", title: "阻塞诊断", note: "完整展示 finding，不截断正文",
        filters: ["kind", "severity"], empty: "暂无阻塞诊断", render: renderDiagnostics,
      },
      artifacts: {
        endpoint: "artifacts", title: "产物", note: "项目相对路径与证据来源",
        filters: [], query: true, empty: "暂无产物路径", render: renderArtifacts,
      },
    };
    const config = configs[state.activeRunTab];
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading(config.title, config.note));
    const toolbar = buildRunToolbar(config);
    if (toolbar) wrapper.append(toolbar);
    const host = node("div", "pager-host");
    wrapper.append(host);
    els.runPanel.replaceChildren(wrapper);
    const pager = runPager(config, host);
    hydrateRunToolbar(pager, config);
    await pager.load();
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
    if (config.filters.includes("status")) toolbar.append(selectFilter("status", "状态", [["", "全部状态"], ["pass", "通过"], ["failed", "失败"], ["blocked", "阻塞"], ["pending", "等待"]]));
    if (config.filters.includes("stream")) toolbar.append(selectFilter("stream", "日志流", [["", "全部日志"], ["stdout", "stdout"], ["stderr", "stderr"]]));
    if (config.filters.includes("severity")) toolbar.append(selectFilter("severity", "严重性", [["", "全部严重性"], ["must_fix", "必须修复"], ["should_fix", "建议修复"]]));
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
    els.runToolbar.replaceChildren();
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
      control.addEventListener("change", () => pager.setFilter(control.dataset.filter, control.value));
    });
    const query = els.runPanel.querySelector("[data-query]");
    if (query && config.query) {
      query.value = pager.state.query;
      query.addEventListener("change", () => pager.setQuery(query.value));
    }
  }

  function renderRunHeader(detail) {
    els.runTitle.textContent = text(detail.run_id, "运行详情");
    els.runSubtitle.textContent = runSummary(detail);
    els.runHero.replaceChildren(node("span", "status-chip warn", phaseLabel(detail.phase || detail.status)));
  }

  function renderRunSummary(detail) {
    const summary = detail.reader_summary && typeof detail.reader_summary === "object" ? detail.reader_summary : {};
    const content = metrics([
      ["当前阶段", phaseLabel(detail.phase)],
      ["下一动作", actionLabel(detail.next_action)],
      ["策略", policyLabel(detail.policy)],
      ["是否需要决策", text(summary.decision_needed, "不可用")],
    ]);
    const purpose = node("div", "run-purpose full-text");
    purpose.append(
      node("strong", "", "任务目标"),
      node("div", "", text(detail.requirement || summary.purpose, "暂无任务说明")),
      node("div", "cell-detail", `当前进展：${text(summary.current_progress, "暂无数据")}`),
      node("div", "cell-detail", `下一步：${text(summary.next_step, "暂无数据")}`),
    );
    els.runOverview.replaceChildren(content, purpose);
  }

  function renderEvents(target, items) {
    renderTable(target, ["时间", "类型", "事件", "来源"], items.map((item) => [
      formatTime(item.updated_at || item.timestamp),
      text(item.kind || item.event_type, "未分类"),
      multiText(item.message || item.summary, readableValue(item.details, "")),
      text(item.source, "不可用"),
    ]));
  }

  function renderChildren(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const summary = item.reader_summary && typeof item.reader_summary === "object" ? item.reader_summary : {};
      const child = node("article", "list-item");
      const heading = node("div", "list-row");
      heading.append(node("strong", "full-text", text(item.requirement || item.run_id)), statusText(item.status || item.phase));
      child.append(
        heading,
        node("div", "cell-detail full-text", `目标：${text(summary.purpose || item.requirement, "暂无")}`),
        node("div", "cell-detail full-text", `Agent 动作：${text(summary.current_progress || item.next_action, "暂无")}`),
        node("div", "cell-detail full-text", `验收：${readableValue(item.acceptance || item.aggregate_acceptance, "暂无")}`),
        node("div", "cell-detail full-text", `产物：${readableValue(item.artifact_paths, "暂无")}`),
      );
      list.append(child);
    });
    target.append(list);
  }

  function renderAgentResults() {
    const detail = state.detail || {};
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading("Agent 结果", "Planner、Generator 和 Evaluator 的完整可读摘要"));
    const agents = node("div", "agent-grid");
    ["planner", "generator", "evaluator"].forEach((name) => {
      const payload = agentPayload(detail, name);
      const item = node("article", "list-item");
      item.append(
        node("strong", "", agentName(name)),
        node("div", "cell-detail full-text", `状态：${agentStatusLabel(payload.status || payload.result)}`),
        node("div", "cell-detail full-text", `动作：${text(payload.action || payload.current_action, "暂无数据")}`),
        node("div", "cell-detail full-text", `结论：${readableValue(payload.summary || payload.findings || payload.reason, "暂无数据")}`),
      );
      agents.append(item);
    });
    wrapper.append(agents);
    els.runPanel.replaceChildren(wrapper);
  }

  function renderAcceptance(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const row = node("article", "list-item");
      row.append(
        node("strong", "full-text", text(item.title || item.scenario_id || item.name, "验收场景")),
        statusText(item.status || item.verdict),
        node("div", "cell-detail full-text", text(item.summary || item.verdict_reason || item.message, "暂无验收说明")),
        node("div", "cell-detail full-text", readableValue(item.findings || item.evidence || item.diagnostics, "暂无附加证据")),
      );
      list.append(row);
    });
    target.append(list);
  }

  function renderLogs(target, items) {
    const list = node("div", "log-list");
    items.forEach((item) => {
      const row = node("article", "log-row");
      const heading = node("div", "list-row");
      heading.append(
        node("strong", "full-text", text(item.name || item.path || item.source || item.log_id, "日志")),
        node("span", "status-text", text(item.stream, "日志")),
      );
      const button = node("button", "link-button", "展开日志详情");
      button.type = "button";
      button.dataset.logDetail = item.log_id;
      const detail = node("pre", "log-detail");
      detail.dataset.logDetailPanel = item.log_id;
      detail.hidden = true;
      button.addEventListener("click", () => expandLogDetail(item.log_id, button, detail));
      row.append(
        heading,
        node("div", "cell-detail full-text", text(item.summary, "列表未提供内容摘要")),
        node("div", "cell-detail", `${text(item.total_bytes || item.size, "大小不可用")} bytes · ${formatTime(item.updated_at)}`),
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
      button.textContent = detail.truncated ? "收起日志详情（内容已截断）" : "收起日志详情";
    } catch (error) {
      detailPanel.textContent = error.message || "日志详情不可用";
      detailPanel.hidden = false;
      button.textContent = "重试日志详情";
    } finally {
      button.disabled = false;
    }
  }

  function renderDiagnostics(target, items) {
    const list = node("div", "list");
    items.forEach((item) => {
      const row = node("article", "list-item");
      row.append(
        node("strong", "full-text", text(item.title || item.kind, "诊断")),
        node("div", "cell-detail full-text", text(item.summary || item.message, "暂无诊断说明")),
        node("div", "cell-detail full-text", readableValue(item.finding || item.evidence || item.details, "暂无附加证据")),
      );
      list.append(row);
    });
    target.append(list);
  }

  function renderArtifacts(target, items) {
    renderTable(target, ["产物", "类型", "来源", "状态"], items.map((item) => [
      multiText(item.path || item.artifact_path || item.name, item.summary),
      text(item.kind || item.type, "未分类"),
      text(item.source, "不可用"),
      statusText(item.status || "available"),
    ]));
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
    });
  }

  function agentPayload(detail, name) {
    const agents = detail.agents && typeof detail.agents === "object" ? detail.agents : {};
    const direct = detail[name] && typeof detail[name] === "object" ? detail[name] : {};
    const status = detail.agent_status && typeof detail.agent_status === "object" ? detail.agent_status[name] : null;
    return agents[name] || direct || (status && typeof status === "object" ? status : { status });
  }

  function runSummary(run) {
    const reader = run.reader_summary && typeof run.reader_summary === "object" ? run.reader_summary : {};
    return text(run.requirement || reader.purpose || run.summary, "暂无任务说明");
  }

  function phaseLabel(value) {
    const labels = {
      planned: "已计划", child_running: "子任务运行中", generating: "生成中", evaluating: "验收中",
      passed: "通过", passed_waiting_human_merge: "通过，等待人工合并", stopped_budget: "停止：预算耗尽",
      stopped_blocked: "停止：阻塞", stopped_no_action: "停止：无需操作", repair_needed: "需要修复",
    };
    return labels[value] || text(value, "不可用");
  }

  function actionLabel(value) {
    const labels = {
      run_parent_planner: "运行父 Planner", run_child_planner: "运行子任务 Planner",
      run_generator: "运行 Generator", run_evaluator: "运行 Evaluator", repair_child: "修复子任务",
      await_human_merge_confirmation: "等待人工合并确认", none: "暂无",
    };
    return labels[value] || text(value, "不可用");
  }

  function policyLabel(value) {
    const labels = { demand_development: "需求开发", autonomous_knowledge: "自主知识拓展" };
    return labels[value] || text(value, "策略不可用");
  }

  function agentName(value) {
    return { planner: "Planner", generator: "Generator", evaluator: "Evaluator" }[value] || value;
  }

  function agentStatusLabel(value) {
    const labels = {
      done: "完成",
      running: "运行中",
      waiting: "等待",
      blocked: "阻塞",
      skipped: "跳过",
      failed: "失败",
    };
    return labels[value] || text(value, "暂无数据");
  }

  function message(value, className) {
    return node("div", className, value);
  }

  boot().catch((error) => {
    els.topStatus.replaceChildren(message(`初始化失败：${error.message}`, "error-state"));
  });
}());
