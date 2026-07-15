(function () {
  "use strict";

  const { CursorPager, fetchPage } = window.LoopPagination;

  const STATUS_LABELS = {
    available: "可用",
    healthy: "正常",
    pending: "待执行",
    leased: "已分配",
    running: "执行中",
    completed: "已完成",
    complete: "已完成",
    failed: "失败",
    cancelled: "已取消",
    open: "待处理",
    closed: "已解决",
    review_complete: "审视完成",
    review_degraded: "Reviewer 暂时不可用",
    fresh: "通过",
    stale: "过期",
    unavailable: "不可用",
  };

  const DECISION_LABELS = {
    continue: "继续",
    auto_remediate: "自动整改",
    refocus: "重新聚焦",
    stop_run: "停止运行",
    ask_user: "请求用户决策",
  };

  class SupervisorView {
    constructor(options) {
      this.panel = options.panel;
      this.hero = options.hero;
      this.topStatus = options.topStatus;
      this.navStatus = options.navStatus;
      this.fetchJson = options.fetchJson;
      this.activeTab = new URL(window.location.href).searchParams.get("supervisor_tab") || "overview";
      this.pagers = new Map();
      this.summary = null;
      this.requestSequence = 0;
      this.bindTabs();
    }

    bindTabs() {
      document.querySelectorAll("[data-supervisor-tab]").forEach((button) => {
        button.addEventListener("click", () => this.selectTab(button.dataset.supervisorTab));
      });
    }

    async show() {
      this.syncTabs();
      await this.loadActiveTab();
    }

    async selectTab(tab) {
      const allowed = ["overview", "services", "recovery", "reviewer", "decisions", "skills", "config"];
      if (!allowed.includes(tab)) return;
      this.activeTab = tab;
      const url = new URL(window.location.href);
      url.searchParams.set("supervisor_tab", tab);
      window.history.replaceState({}, "", url);
      this.syncTabs();
      await this.loadActiveTab();
    }

    syncTabs() {
      document.querySelectorAll("[data-supervisor-tab]").forEach((button) => {
        const selected = button.dataset.supervisorTab === this.activeTab;
        button.classList.toggle("is-active", selected);
        button.setAttribute("aria-selected", String(selected));
      });
    }

    async loadActiveTab() {
      const request = ++this.requestSequence;
      this.panel.replaceChildren(messageNode("正在读取...", "empty-state"));
      try {
        if (this.activeTab === "overview") await this.renderOverview(request);
        else if (this.activeTab === "services") await this.renderServices(request);
        else if (this.activeTab === "recovery") await this.renderRecovery(request);
        else if (this.activeTab === "reviewer") await this.renderReviewer(request);
        else if (this.activeTab === "decisions") await this.renderDecisions(request);
        else if (this.activeTab === "skills") await this.renderSkills(request);
        else await this.renderConfig(request);
      } catch (error) {
        if (request !== this.requestSequence) return;
        this.panel.replaceChildren(messageNode(error.message || "Supervisor 数据不可用", "error-state"));
        this.setHealth(false, "Supervisor 不可用");
      }
    }

    async loadSummary() {
      const summary = await this.fetchJson("/api/supervisor");
      if (summary.status !== "available") {
        const message = summary.error?.message || summary.diagnostics?.join("；") || "Supervisor 数据不可用";
        throw new Error(message);
      }
      this.summary = summary;
      this.setHealth(true, "Supervisor 正常");
      return summary;
    }

    setHealth(available, label) {
      this.navStatus.textContent = available ? "正常" : "不可用";
      this.navStatus.className = `status-text ${available ? "good" : "bad"}`;
      this.topStatus.replaceChildren(
        chip(label, available ? "good" : "bad"),
        chip(available ? "统一控制面已连接" : "数据不可用", available ? "good" : "warn"),
        chip("无独立控制角色", "neutral"),
      );
    }

    updateHero(summary) {
      const counts = summary.counts || {};
      this.hero.replaceChildren(
        chip(`${valueText(counts.workers)} Worker 记录`, counts.workers ? "good" : "warn"),
        chip(`${valueText(counts.user_decisions)} 项决策记录`, "neutral"),
        chip(`${valueText(counts.actions)} 项动作记录`, "neutral"),
      );
    }

    async renderOverview(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const counts = summary.counts || {};
      const content = document.createDocumentFragment();
      content.append(metrics([
        ["运行记录", valueText(counts.runs)],
        ["动作记录", valueText(counts.actions)],
        ["Reviewer 记录", valueText(counts.reviews)],
        ["用户决策记录", valueText(counts.user_decisions)],
      ]));
      content.append(section("控制流程", "一个注册表 · 一个动作队列 · 一个决策入口", flow([
        ["Reconciler", "读取 run.json 和证据"],
        ["Decision Engine", "计算下一状态与恢复层级"],
        ["Action Queue", "SQLite 幂等动作与租约"],
        ["Worker", "执行 Planner / Generator / Evaluator"],
        ["Reviewer", "按项目级节奏审视"],
      ])));
      const split = node("div", "split");
      split.append(
        section("当前动作", "详情在任务恢复页", messageNode(
          counts.actions ? `共有 ${counts.actions} 条动作记录；当前状态需在任务恢复页查看。` : "暂无动作记录",
          "list-item",
        )),
        section("最近全局判断", "详情在 Reviewer 页", messageNode(
          counts.reviews ? `共有 ${counts.reviews} 条 Reviewer 记录；最近结论需在 Reviewer 页查看。` : "暂无 Reviewer 记录",
          "list-item",
        )),
      );
      content.append(split);
      this.panel.replaceChildren(content);
    }

    async renderServices(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const container = pagerSection(this.panel, "服务状态", "可达性、进程、版本和数据新鲜度分别判断");
      const pager = this.pager("supervisor-services", {
        endpoint: "/api/supervisor/services",
        container,
        allowedFilters: ["status"],
        emptyMessage: "暂无服务数据",
        renderItems: (target, items) => renderTable(target, ["服务", "可达", "进程 / 心跳", "版本", "数据新鲜度"], items.map((item) => {
          const details = objectValue(item.details);
          return [
            strongText(item.service_id),
            statusText(item.status),
            text(item.process_id || item.heartbeat_at, "不可用"),
            text(item.version, "不可用"),
            text(details.freshness || details.data_freshness || details.summary, "暂无数据"),
          ];
        })),
      });
      await pager.load();
    }

    async renderRecovery(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const wrapper = node("section", "section");
      wrapper.append(sectionHeading("任务恢复", "同一 failure key 更新次数，不按 tick 重复追加"));
      const toolbar = node("div", "toolbar");
      const controls = node("div", "filters");
      const status = selectControl("动作状态", [
        ["", "全部状态"], ["pending", "待执行"], ["running", "执行中"], ["completed", "已完成"], ["failed", "失败"],
      ]);
      const runId = inputControl("运行 ID", "按完整 run ID 过滤");
      controls.append(status.label, runId.label);
      toolbar.append(controls);
      const container = node("div", "pager-host");
      wrapper.append(toolbar, container);
      this.panel.replaceChildren(wrapper);
      const pager = this.pager("supervisor-recovery", {
        endpoint: "/api/supervisor/actions",
        container,
        allowedFilters: ["status", "run_id"],
        emptyMessage: "暂无恢复动作",
        renderItems: (target, items) => renderTable(target, ["运行 / 动作", "恢复判断", "层级", "状态"], items.map((item) => [
          multiText(item.run_id, item.action_id),
          multiText(actionLabel(item.action_type), text(objectValue(item.payload).summary || objectValue(item.payload).reason, "暂无说明")),
          `Tier ${Number(item.recovery_tier || 0)}`,
          statusText(item.status),
        ])),
      });
      status.select.value = pager.state.filters.status || "";
      runId.input.value = pager.state.filters.run_id || "";
      status.select.addEventListener("change", () => pager.setFilter("status", status.select.value));
      runId.input.addEventListener("change", () => pager.setFilter("run_id", runId.input.value.trim()));
      await pager.load();
    }

    async renderReviewer(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const content = document.createDocumentFragment();
      content.append(metrics([
        ["审视范围", "项目全局"],
        ["常规节奏", "由 Supervisor 配置"],
        ["审视记录", valueText(summary.counts?.reviews)],
        ["开放 finding", valueText(summary.counts?.review_findings)],
      ]));
      const container = pagerSection(content, "Reviewer 历史", "Reviewer 不可用时如实显示降级状态");
      this.panel.replaceChildren(content);
      const pager = this.pager("supervisor-reviewer", {
        endpoint: "/api/supervisor/reviews",
        container,
        allowedFilters: ["status", "decision", "trigger"],
        emptyMessage: "暂无 Reviewer 记录",
        renderItems: (target, items) => renderTable(target, ["时间", "全局判断", "证据范围", "自动动作"], items.map((item) => [
          formatTime(item.created_at),
          multiText(decisionLabel(item.decision), item.summary),
          readableValue(item.evidence, "暂无证据范围"),
          statusText(item.status),
        ])),
      });
      await pager.load();
    }

    async renderDecisions(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const wrapper = node("section", "section");
      wrapper.append(sectionHeading("决策", "人工决策默认只影响单个 run"));
      const status = selectControl("决策状态", [["", "全部决策"], ["open", "需要用户"], ["closed", "已解决"]]);
      const toolbar = node("div", "toolbar");
      toolbar.append(status.label);
      const container = node("div", "pager-host");
      wrapper.append(toolbar, container);
      this.panel.replaceChildren(wrapper);
      const pager = this.pager("supervisor-decisions", {
        endpoint: "/api/supervisor/decisions",
        container,
        allowedFilters: ["status", "scope", "run_id"],
        emptyMessage: "暂无决策记录",
        renderItems: (target, items) => renderTable(target, ["对象", "决策", "原因", "影响范围"], items.map((item) => [
          text(item.run_id, item.scope === "global" ? "项目" : "不可用"),
          statusText(item.status),
          multiText(item.summary, item.required_decision || item.resolution),
          item.scope === "global" ? "全局" : "仅当前 run",
        ])),
      });
      status.select.value = pager.state.filters.status || "";
      status.select.addEventListener("change", () => pager.setFilter("status", status.select.value));
      await pager.load();
    }

    async renderSkills(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const snapshots = await fetchPage("/api/supervisor/skills", {
        cursor: null, pageSize: 20, query: "", sort: "newest", filters: {},
      });
      if (request !== this.requestSequence) return;
      const snapshot = snapshots.items[0];
      if (!snapshot) {
        this.panel.replaceChildren(messageNode("暂无 Skill 快照", "empty-state"));
        return;
      }
      const content = document.createDocumentFragment();
      content.append(metrics([
        ["项目 Skill", valueText(snapshot.total_skills)],
        ["证据确认使用", valueText(snapshot.used_skills)],
        ["重复组", valueText(snapshot.duplicate_group_count)],
        ["待治理建议", valueText(snapshot.recommendation_count)],
      ]));
      const container = pagerSection(content, "Skill 治理", "日志字符串匹配不作为使用证明");
      this.panel.replaceChildren(content);
      const pager = this.pager(`supervisor-skills-${snapshot.snapshot_id}`, {
        endpoint: `/api/supervisor/skills/${encodeURIComponent(snapshot.snapshot_id)}/rows`,
        container,
        allowedFilters: [],
        emptyMessage: "当前快照没有 Skill 行",
        renderItems: (target, items) => renderTable(target, ["Skill", "证据", "Reviewer 判断", "建议"], items.map((item) => [
          strongText(item.name || item.path || item.skill_id),
          readableValue(item.evidence || item.confirmed_usage, "暂无使用证据"),
          text(item.reviewer_summary || item.summary || item.status, "暂无判断"),
          text(item.recommendation || item.action, "暂无建议"),
        ])),
      });
      await pager.load();
    }

    async renderConfig(request) {
      const summary = await this.loadSummary();
      if (request !== this.requestSequence) return;
      this.updateHero(summary);
      const split = node("div", "split");
      split.append(
        section("恢复策略", "Task 7 未提供配置读取 API", definitionList([
          ["原动作重试", "不可用"], ["替代恢复", "不可用"], ["Worker 租约", "不可用"],
        ])),
        section("审视与保留", "未从运行配置读取", definitionList([
          ["Reviewer cadence", "不可用"], ["详细历史", "不可用"], ["导出轮转", "不可用"],
        ])),
      );
      const degraded = section("降级状态", "当前数据契约", messageNode(
        `数据库 schema v${text(summary.schema_version, "不可用")}；未启用配置读取接口，不能推断运行参数。`,
        "list-item",
      ));
      this.panel.replaceChildren(split, degraded);
    }

    pager(key, options) {
      const existing = this.pagers.get(key);
      if (existing) {
        existing.container = options.container;
        existing.renderItems = options.renderItems;
        return existing;
      }
      const pager = new CursorPager({ key, ...options });
      this.pagers.set(key, pager);
      return pager;
    }
  }

  function pagerSection(parent, title, note) {
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading(title, note));
    const container = node("div", "pager-host");
    wrapper.append(container);
    parent.append(wrapper);
    return container;
  }

  function section(title, note, content) {
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading(title, note), content);
    return wrapper;
  }

  function sectionHeading(title, note) {
    const heading = node("div", "section-head");
    heading.append(node("h3", "", title));
    if (note) heading.append(node("span", "section-note", note));
    return heading;
  }

  function metrics(values) {
    const wrapper = node("div", "metrics");
    values.forEach(([label, value]) => {
      const metric = node("div", "metric");
      metric.append(node("div", "metric-label", label), node("div", "metric-value", value));
      wrapper.append(metric);
    });
    return wrapper;
  }

  function flow(values) {
    const wrapper = node("div", "flow");
    values.forEach(([title, detail]) => {
      const item = node("div", "flow-node");
      item.append(node("strong", "", title), node("span", "", detail));
      wrapper.append(item);
    });
    return wrapper;
  }

  function renderTable(target, headers, rows) {
    const wrap = node("div", "table-wrap");
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    headers.forEach((header) => headerRow.append(node("th", "", header)));
    head.append(headerRow);
    const body = document.createElement("tbody");
    rows.forEach((cells) => {
      const row = document.createElement("tr");
      cells.forEach((cell) => {
        const td = document.createElement("td");
        if (cell instanceof Node) td.append(cell);
        else td.textContent = text(cell);
        row.append(td);
      });
      body.append(row);
    });
    table.append(head, body);
    wrap.append(table);
    target.append(wrap);
  }

  function definitionList(rows) {
    const list = node("div", "list");
    rows.forEach(([label, value]) => {
      const item = node("div", "list-item list-row");
      item.append(node("strong", "", label), node("span", "", value));
      list.append(item);
    });
    return list;
  }

  function selectControl(labelText, options) {
    const label = node("label", "filter-control");
    const select = node("select", "control");
    select.setAttribute("aria-label", labelText);
    options.forEach(([value, labelTextValue]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labelTextValue;
      select.append(option);
    });
    label.append(node("span", "", labelText), select);
    return { label, select };
  }

  function inputControl(labelText, placeholder) {
    const label = node("label", "filter-control");
    const input = node("input", "control");
    input.type = "search";
    input.placeholder = placeholder;
    input.setAttribute("aria-label", labelText);
    label.append(node("span", "", labelText), input);
    return { label, input };
  }

  function chip(label, tone) {
    return node("span", `status-chip ${tone || "neutral"}`, label);
  }

  function messageNode(message, className) {
    return node("div", className, message);
  }

  function multiText(title, detail) {
    const wrapper = node("div", "cell-stack");
    wrapper.append(node("div", "cell-title", text(title)));
    if (detail) wrapper.append(node("div", "cell-detail", text(detail)));
    return wrapper;
  }

  function strongText(value) {
    return node("span", "cell-title", text(value));
  }

  function statusText(value) {
    const normalized = String(value || "unavailable");
    const tone = ["healthy", "completed", "complete", "fresh", "review_complete", "closed"].includes(normalized)
      ? "good"
      : ["failed", "cancelled"].includes(normalized) ? "bad" : "warn";
    return node("span", `status-text ${tone}`, STATUS_LABELS[normalized] || `未识别状态（${normalized}）`);
  }

  function actionLabel(value) {
    const labels = {
      run_planner: "运行 Planner", run_generator: "运行 Generator", run_evaluator: "运行 Evaluator",
      recover_partial_artifact: "恢复部分产物", recover_generator_result: "恢复 Generator 结果",
      run_alternate_recovery: "运行替代恢复", restart_service: "重启服务", ask_user: "请求用户决策",
    };
    return labels[value] || text(value, "未识别动作");
  }

  function decisionLabel(value) {
    return DECISION_LABELS[value] || text(value, "暂无结论");
  }

  function formatTime(value) {
    if (!value) return "不可用";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", { hour12: false });
  }

  function readableValue(value, fallback) {
    if (Array.isArray(value)) return value.length ? value.map((item) => readableValue(item, "")).join("；") : fallback;
    if (value && typeof value === "object") {
      const parts = Object.entries(value).map(([key, item]) => `${key}：${readableValue(item, "暂无")}`);
      return parts.length ? parts.join("；") : fallback;
    }
    return text(value, fallback);
  }

  function objectValue(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function valueText(value) {
    return Number.isInteger(value) ? String(value) : "不可用";
  }

  function text(value, fallback = "暂无数据") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function node(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined && content !== null) element.textContent = String(content);
    return element;
  }

  window.LoopSupervisor = { SupervisorView, renderTable, section, sectionHeading, metrics, node, text, readableValue, statusText, multiText, formatTime };
}());
