(function () {
  "use strict";

  const { CursorPager, DashboardError, fetchPage } = window.LoopPagination;
  const SUPERVISOR_TABS = ["overview", "services", "recovery", "reviewer", "decisions", "skills", "config"];

  class SupervisorView {
    constructor(options) {
      this.panel = options.panel;
      this.hero = options.hero;
      this.topStatus = options.topStatus;
      this.navStatus = options.navStatus;
      this.fetchJson = options.fetchJson;
      const requested = new URL(window.location.href).searchParams.get("supervisor_tab") || "overview";
      this.activeTab = SUPERVISOR_TABS.includes(requested) ? requested : "overview";
      this.canonicalizeActiveTab(requested);
      this.pagers = new Map();
      this.recoveryAttemptPagers = new Map();
      this.activePagerKeys = [];
      this.summary = null;
      this.requestSequence = 0;
      this.viewAbortController = null;
      this.isActive = false;
      this.bindTabs();
    }

    canonicalizeActiveTab(requested) {
      const url = new URL(window.location.href);
      if (requested !== this.activeTab) url.searchParams.set("supervisor_tab", this.activeTab);
      window.history.replaceState({}, "", url);
    }

    bindTabs() {
      const tabs = Array.from(document.querySelectorAll("[data-supervisor-tab]"));
      tabs.forEach((button, index) => {
        button.addEventListener("click", () => this.selectTab(button.dataset.supervisorTab));
        button.addEventListener("keydown", (event) => {
          let targetIndex = -1;
          if (event.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
          if (event.key === "Home") targetIndex = 0;
          if (event.key === "End") targetIndex = tabs.length - 1;
          if (targetIndex < 0) return;
          event.preventDefault();
          tabs[targetIndex].focus();
          this.selectTab(tabs[targetIndex].dataset.supervisorTab);
        });
      });
    }

    async show() {
      this.isActive = true;
      this.syncTabs();
      await this.loadActiveTab();
    }

    async refresh() {
      if (!this.isActive) return;
      await this.loadActiveTab({ refresh: true });
    }

    deactivate() {
      this.isActive = false;
      this.requestSequence += 1;
      if (this.viewAbortController) this.viewAbortController.abort();
      this.viewAbortController = null;
      this.activePagerKeys.forEach((key) => this.pagers.get(key)?.destroy());
      this.recoveryAttemptPagers.forEach((pager) => pager.destroy());
      this.activePagerKeys = [];
    }

    async selectTab(tab) {
      if (!SUPERVISOR_TABS.includes(tab) || !this.isActive) return;
      if (this.viewAbortController) this.viewAbortController.abort();
      this.activePagerKeys.forEach((key) => this.pagers.get(key)?.destroy());
      this.recoveryAttemptPagers.forEach((pager) => pager.destroy());
      this.activePagerKeys = [];
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
        button.setAttribute("tabindex", selected ? "0" : "-1");
        if (selected) this.panel.setAttribute("aria-labelledby", button.id);
      });
    }

    async loadActiveTab(options = {}) {
      if (!this.isActive) return;
      if (this.viewAbortController) this.viewAbortController.abort();
      this.viewAbortController = new AbortController();
      const signal = this.viewAbortController.signal;
      const request = ++this.requestSequence;
      if (!options.refresh) this.panel.replaceChildren(messageNode("正在读取...", "empty-state"));
      try {
        if (this.activeTab === "overview") await this.renderOverview(request, signal);
        else if (this.activeTab === "services") await this.renderServices(request, signal, options);
        else if (this.activeTab === "recovery") await this.renderRecovery(request, signal, options);
        else if (this.activeTab === "reviewer") await this.renderReviewer(request, signal, options);
        else if (this.activeTab === "decisions") await this.renderDecisions(request, signal, options);
        else if (this.activeTab === "skills") await this.renderSkills(request, signal, options);
        else await this.renderConfig(request, signal);
      } catch (error) {
        if (!this.isCurrentRequest(request, signal) || error.name === "AbortError") return;
        this.panel.replaceChildren(messageNode(errorText(error), "error-state"));
        this.setHealth("unchecked", "健康状态未检查");
      }
    }

    isCurrentRequest(request, signal) {
      return this.isActive && request === this.requestSequence && !signal.aborted;
    }

    async loadSummary(signal) {
      const summary = await this.fetchJson("/api/supervisor", { signal });
      if (summary.status !== "available") {
        const diagnostic = objectValue(summary.error);
        const message = structuredDiagnosticText({
          status: summary.status,
          code: diagnostic.code,
          message: diagnostic.message,
          diagnostics: summary.diagnostics,
        });
        throw new DashboardError(diagnostic.code || summary.status || "unavailable", message, { payload: summary });
      }
      this.summary = summary;
      return summary;
    }

    setHealth(mode, label) {
      const tone = mode === "healthy" ? "good" : mode === "degraded" ? "warn" : mode === "unchecked" ? "neutral" : "bad";
      this.navStatus.textContent = mode === "healthy" ? "正常" : mode === "degraded" ? "降级" : mode === "unchecked" ? "未检查" : "不可用";
      this.navStatus.className = `status-text ${tone}`;
      this.topStatus.replaceChildren(
        chip(label, tone),
        chip(
          mode === "healthy"
            ? "服务与 freshness 全量验证"
            : mode === "degraded"
              ? "数据可读，服务或 freshness 未全部健康"
              : mode === "unchecked"
                ? "服务与 freshness 未检查"
                : "健康状态不可用",
          tone,
        ),
        chip("无独立控制角色", "neutral"),
      );
    }

    deriveHealth(summary, services, freshness, coverageComplete) {
      const rows = services?.items || [];
      const freshnessRows = freshness?.items || [];
      if (!summary || summary.status !== "available" || !rows.length) {
        this.setHealth("unchecked", summary ? "Supervisor 数据可读，健康未检查" : "健康状态未检查");
        return;
      }
      const allHealthy = rows.every((service) => service.status === "healthy");
      const allFresh = freshnessRows.length > 0 && freshnessRows.every((item) => ["fresh", "pass"].includes(item.status));
      const workers = summary.counts?.workers;
      if (coverageComplete && allHealthy && allFresh && Number.isInteger(workers) && workers > 0) {
        this.setHealth("healthy", "Supervisor 正常");
      }
      else this.setHealth("degraded", "Supervisor 降级");
    }

    updateHero(summary, services, freshness, coverageComplete) {
      const rows = services?.items || [];
      const healthy = rows.filter((item) => item.status === "healthy").length;
      const freshnessRows = freshness?.items || [];
      const fresh = freshnessRows.filter((item) => ["fresh", "pass"].includes(item.status)).length;
      this.hero.replaceChildren(
        chip(rows.length ? `${healthy} / ${services.total} 服务健康` : "服务健康未检查", coverageComplete && healthy === services?.total ? "good" : "warn"),
        chip(freshnessRows.length ? `${fresh} / ${freshness.total} freshness 通过` : "freshness 未覆盖", coverageComplete && fresh === freshness?.total ? "good" : "warn"),
        chip(`${valueText(summary.counts?.workers)} Worker 记录`, summary.counts?.workers ? "good" : "warn"),
      );
    }

    async loadHealthEvidence(signal) {
      const services = await fetchAllPages("/api/supervisor/services", signal);
      const freshness = await fetchAllPages("/api/supervisor/services/freshness", signal);
      return {
        services,
        freshness,
        coverageComplete: services.coverageComplete && freshness.coverageComplete,
      };
    }

    async renderOverview(request, signal) {
      const summary = await this.loadSummary(signal);
      const pendingActions = await firstPage("/api/supervisor/actions", { status: "pending" }, signal);
      const reviews = await firstPage("/api/supervisor/reviews", {}, signal);
      const required = await firstPage("/api/supervisor/decision-required", {}, signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const recentReview = reviews.items[0];
      const content = document.createDocumentFragment();
      content.append(metrics([
        ["活动运行", "不可用"],
        ["待执行动作", valueText(pendingActions.total)],
        ["最近 Reviewer", recentReview ? reviewDecisionLabel(recentReview.decision) : "暂无数据"],
        ["需要用户", valueText(required.total)],
      ]));
      content.append(node("div", "metric-disclosure", "活动运行：Task 7 未提供活动运行聚合，不能用运行总数代替。"));
      content.append(section("控制流程", "一个注册表 · 一个动作队列 · 一个决策入口", flow([
        ["Reconciler", "读取 run.json 和证据"],
        ["Decision Engine", "计算下一状态与恢复层级"],
        ["Action Queue", "SQLite 幂等动作与租约"],
        ["Worker", "执行 Planner / Generator / Evaluator"],
        ["Reviewer", "按项目级节奏审视"],
      ])));
      const split = node("div", "split");
      split.append(
        section("当前动作", "任务恢复页提供完整记录", pendingActions.items[0]
          ? actionSummary(pendingActions.items[0])
          : messageNode("暂无待执行动作", "list-item")),
        section("最近全局判断", "Reviewer 请求动作来自 accepted review", recentReview
          ? reviewSummary(recentReview)
          : messageNode("暂无 Reviewer 记录", "list-item")),
      );
      content.append(split);
      this.panel.replaceChildren(content);
    }

    async renderServices(request, signal, options) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const fragment = document.createDocumentFragment();
      const servicesHost = pagerSection(fragment, "服务状态", "可达性、进程、版本和数据新鲜度分别判断");
      const freshnessHost = pagerSection(fragment, "数据新鲜度", "目标、检查状态、摘要和证据明细");
      this.panel.replaceChildren(fragment);
      const servicesPager = this.pager("supervisor-services", {
        endpoint: "/api/supervisor/services",
        container: servicesHost,
        allowedFilters: ["status"],
        emptyMessage: "暂无服务数据",
        renderItems: (target, items) => renderTable(target, ["服务", "健康", "可达", "进程 / 心跳", "版本", "数据新鲜度"], items.map((item) => {
          const details = objectValue(item.details);
          return [
            strongText(serviceNameLabel(item.service_id)),
            statusText(serviceHealthLabel(item.status), serviceHealthTone(item.status)),
            booleanLabel(details.reachable),
            text(item.process_id || item.heartbeat_at, "不可用"),
            text(item.version, "不可用"),
            text(details.freshness || details.data_freshness, "暂无 freshness target"),
          ];
        })),
      });
      const freshnessPager = this.pager("supervisor-freshness", {
        endpoint: "/api/supervisor/services/freshness",
        container: freshnessHost,
        allowedFilters: ["target", "status"],
        emptyMessage: "暂无 freshness target",
        renderItems: (target, items) => renderTable(target, ["目标", "状态", "摘要", "检查时间", "明细"], items.map((item) => [
          strongText(item.target),
          statusText(freshnessLabel(item.status), freshnessTone(item.status)),
          text(item.summary, "暂无摘要"),
          formatTime(item.checked_at || item.created_at),
          readableValue(item.details, "暂无明细"),
        ])),
      });
      await loadPager(servicesPager, options.refresh);
      if (!this.isCurrentRequest(request, signal)) return;
      await loadPager(freshnessPager, options.refresh);
    }

    async renderRecovery(request, signal, options) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const wrapper = node("section", "section");
      wrapper.append(sectionHeading("任务恢复", "动作与恢复尝试均来自 Task 7 分页接口"));
      const toolbar = node("div", "toolbar");
      const controls = node("div", "filters");
      const status = selectControl("动作状态", [
        ["", "全部状态"], ["pending", "待执行"], ["running", "执行中"], ["completed", "已完成"], ["failed", "失败"],
      ]);
      const runId = inputControl("运行 ID", "按完整 run ID 过滤");
      controls.append(status.label, runId.label);
      toolbar.append(controls);
      const host = node("div", "pager-host");
      wrapper.append(toolbar, host);
      this.panel.replaceChildren(wrapper);
      const pager = this.pager("supervisor-recovery", {
        endpoint: "/api/supervisor/actions",
        container: host,
        allowedFilters: ["status", "run_id"],
        emptyMessage: "暂无恢复动作",
        renderItems: (target, items) => renderRecoveryTable(target, items, this),
      });
      status.select.value = pager.state.filters.status || "";
      runId.input.value = pager.state.filters.run_id || "";
      status.select.addEventListener("change", async () => {
        await pager.setFilter("status", status.select.value);
        status.select.value = pager.state.filters.status || "";
      });
      runId.input.addEventListener("change", async () => {
        await pager.setFilter("run_id", runId.input.value.trim());
        runId.input.value = pager.state.filters.run_id || "";
      });
      await loadPager(pager, options.refresh);
    }

    async renderReviewer(request, signal, options) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const fragment = document.createDocumentFragment();
      fragment.append(metrics([
        ["审视范围", "项目全局"],
        ["常规节奏", "不可用"],
        ["审视记录", valueText(summary.counts?.reviews)],
        ["finding 总数", valueText(summary.counts?.review_findings)],
      ]));
      const host = pagerSection(fragment, "Reviewer 历史", "结论、证据范围和请求动作均来自 Reviewer 记录");
      this.panel.replaceChildren(fragment);
      const pager = this.pager("supervisor-reviewer", {
        endpoint: "/api/supervisor/reviews",
        container: host,
        allowedFilters: ["status", "decision", "trigger"],
        emptyMessage: "暂无 Reviewer 记录",
        renderItems: (target, items) => renderTable(target, ["时间", "全局判断", "证据范围", "请求动作", "状态"], items.map((item) => {
          const accepted = objectValue(item.accepted_review);
          return [
            formatTime(item.created_at),
            multiText(reviewDecisionLabel(item.decision), item.summary),
            readableValue(item.evidence, "暂无证据范围"),
            readableValue(accepted.actions || accepted.requested_actions || item.decision, reviewDecisionLabel(item.decision)),
            statusText(reviewStatusLabel(item.status), reviewStatusTone(item.status)),
          ];
        })),
      });
      await loadPager(pager, options.refresh);
    }

    async renderDecisions(request, signal, options) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const wrapper = node("section", "section");
      wrapper.append(sectionHeading("决策", "人工决策默认只影响单个 run"));
      const status = selectControl("决策状态", [["", "全部决策"], ["open", "需要用户"], ["closed", "已解决"]]);
      const toolbar = node("div", "toolbar");
      toolbar.append(status.label);
      const host = node("div", "pager-host");
      wrapper.append(toolbar, host);
      this.panel.replaceChildren(wrapper);
      const pager = this.pager("supervisor-decisions", {
        endpoint: "/api/supervisor/decisions",
        container: host,
        allowedFilters: ["status", "scope", "run_id"],
        emptyMessage: "暂无决策记录",
        renderItems: (target, items) => renderTable(target, ["对象", "状态", "含义", "需要决定", "解决结果", "影响范围"], items.map((item) => [
          text(item.run_id, item.scope === "global" ? "项目" : "不可用"),
          statusText(decisionStatusLabel(item.status), decisionStatusTone(item.status)),
          text(item.summary, "暂无说明"),
          text(item.required_decision, "暂无"),
          text(item.resolution, item.status === "open" ? "尚未解决" : "暂无记录"),
          item.scope === "global" ? "全局" : "仅当前 run",
        ])),
      });
      status.select.value = pager.state.filters.status || "";
      status.select.addEventListener("change", async () => {
        await pager.setFilter("status", status.select.value);
        status.select.value = pager.state.filters.status || "";
      });
      await loadPager(pager, options.refresh);
    }

    async renderSkills(request, signal, options) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      const snapshots = await firstPage("/api/supervisor/skills", {}, signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const snapshot = snapshots.items[0];
      if (!snapshot) {
        this.panel.replaceChildren(messageNode("暂无 Skill 快照", "empty-state"));
        return;
      }
      const fragment = document.createDocumentFragment();
      fragment.append(metrics([
        ["项目 Skill", valueText(snapshot.total_skills)],
        ["证据确认使用", valueText(snapshot.used_skills)],
        ["重复组", valueText(snapshot.duplicate_group_count)],
        ["待治理建议", valueText(snapshot.recommendation_count)],
      ]));
      const host = pagerSection(fragment, "Skill 治理", "日志字符串匹配不作为使用证明");
      this.panel.replaceChildren(fragment);
      const pager = this.pager(`supervisor-skills-${snapshot.snapshot_id}`, {
        endpoint: `/api/supervisor/skills/${encodeURIComponent(snapshot.snapshot_id)}/rows`,
        container: host,
        allowedFilters: [],
        emptyMessage: "当前快照没有 Skill 行",
        renderItems: (target, items) => renderTable(target, ["Skill", "证据", "Reviewer 判断", "建议"], items.map((item) => [
          strongText(item.name || item.path || item.skill_id),
          readableValue(item.evidence || item.confirmed_usage, "暂无使用证据"),
          text(item.reviewer_summary || item.summary || item.status, "暂无判断"),
          text(item.recommendation || item.action, "暂无建议"),
        ])),
      });
      await loadPager(pager, options.refresh);
    }

    async renderConfig(request, signal) {
      const summary = await this.loadSummary(signal);
      const health = await this.loadHealthEvidence(signal);
      if (!this.isCurrentRequest(request, signal)) return;
      this.deriveHealth(summary, health.services, health.freshness, health.coverageComplete);
      this.updateHero(summary, health.services, health.freshness, health.coverageComplete);
      const split = node("div", "split");
      split.append(
        section("恢复策略", "Task 7 未提供配置读取 API", definitionList([
          ["原动作重试", "不可用"], ["替代恢复", "不可用"], ["Worker 租约", "不可用"],
        ])),
        section("审视与保留", "未从运行配置读取", definitionList([
          ["Reviewer cadence", "不可用"], ["详细历史", "不可用"], ["导出轮转", "不可用"],
        ])),
      );
      this.panel.replaceChildren(
        split,
        section("降级状态", "当前数据契约", messageNode(
          `数据库 schema v${text(summary.schema_version, "不可用")}；未启用配置读取接口，不能推断运行参数。`,
          "list-item",
        )),
      );
    }

    createRecoveryAttemptPager(actionId, container) {
      const key = `supervisor-recovery-attempts-${actionId}`;
      const existing = this.recoveryAttemptPagers.get(key);
      if (existing) {
        existing.container = container;
        return existing;
      }
      const pager = new CursorPager({
        key,
        endpoint: `/api/supervisor/actions/${encodeURIComponent(actionId)}/attempts`,
        container,
        allowedFilters: ["result_class", "error_class", "recovery_tier"],
        fixedSort: "newest",
        emptyMessage: "暂无恢复尝试",
        renderItems: (target, items) => {
          const list = node("div", "attempt-list");
          items.forEach((attempt) => list.append(attemptSummary(attempt)));
          target.append(list);
        },
      });
      this.recoveryAttemptPagers.set(key, pager);
      return pager;
    }

    pager(key, options) {
      const existing = this.pagers.get(key);
      if (existing) {
        existing.container = options.container;
        existing.renderItems = options.renderItems;
        if (!this.activePagerKeys.includes(key)) this.activePagerKeys.push(key);
        return existing;
      }
      const pager = new CursorPager({ key, fixedSort: "newest", ...options });
      this.pagers.set(key, pager);
      this.activePagerKeys.push(key);
      return pager;
    }
  }

  async function firstPage(endpoint, filters = {}, signal) {
    return fetchPage(endpoint, { cursor: null, pageSize: 20, query: "", filters }, signal);
  }

  async function fetchAllPages(endpoint, signal) {
    const items = [];
    let cursor = null;
    let total = 0;
    let pages = 0;
    do {
      const page = await fetchPage(endpoint, { cursor, pageSize: 100, query: "", filters: {} }, signal);
      items.push(...page.items);
      total = page.total;
      cursor = page.next_cursor;
      pages += 1;
      if (pages > 1000) throw new DashboardError("page_limit_exceeded", "健康数据分页超过安全上限");
    } while (cursor);
    return { items, total, coverageComplete: items.length === total };
  }

  async function loadPager(pager, refresh) {
    if (refresh && pager.page) return pager.refresh();
    return pager.load();
  }

  function renderRecoveryTable(target, items, supervisorView) {
    const wrap = node("div", "table-wrap");
    const table = document.createElement("table");
    table.innerHTML = "<thead><tr><th>运行 / 动作</th><th>恢复判断</th><th>层级</th><th>状态 / 日志</th></tr></thead>";
    const body = document.createElement("tbody");
    items.forEach((item, index) => {
      const row = document.createElement("tr");
      const actionId = item.action_id;
      const detailId = `recovery-log-${safeDomId(actionId || String(index))}`;
      const statusCell = document.createElement("td");
      const button = node("button", "link-button", "查看恢复日志");
      button.type = "button";
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-controls", detailId);
      const detail = node("div", "recovery-log-detail");
      detail.id = detailId;
      detail.hidden = true;
      button.addEventListener("click", async () => {
        if (button.dataset.loaded === "true") {
          detail.hidden = !detail.hidden;
          button.setAttribute("aria-expanded", String(!detail.hidden));
          button.textContent = detail.hidden ? "查看恢复日志" : "收起恢复日志";
          return;
        }
        button.disabled = true;
        try {
          detail.replaceChildren();
          const pager = supervisorView.createRecoveryAttemptPager(actionId, detail);
          await pager.load();
          detail.hidden = false;
          button.dataset.loaded = "true";
          button.setAttribute("aria-expanded", "true");
          button.textContent = "收起恢复日志";
        } catch (error) {
          detail.replaceChildren(messageNode(errorText(error), "error-state"));
          detail.hidden = false;
          button.setAttribute("aria-expanded", "true");
          button.textContent = "重试恢复日志";
        } finally {
          button.disabled = false;
        }
      });
      statusCell.append(
        statusText(actionStatusLabel(item.status), actionStatusTone(item.status)),
        document.createElement("br"),
        button,
        detail,
      );
      [
        multiText(item.run_id, actionId),
        multiText(actionTypeLabel(item.action_type), text(objectValue(item.payload).summary || objectValue(item.payload).reason, "暂无说明")),
        `Tier ${Number(item.recovery_tier || 0)}`,
        statusCell,
      ].forEach((cell) => {
        if (cell === statusCell) row.append(cell);
        else {
          const td = document.createElement("td");
          if (cell instanceof Node) td.append(cell);
          else td.textContent = String(cell);
          row.append(td);
        }
      });
      body.append(row);
    });
    table.append(body);
    wrap.append(table);
    target.append(wrap);
  }

  function attemptSummary(attempt) {
    const item = node("div", "attempt-row");
    item.append(
      node("strong", "", text(attempt.summary, "恢复尝试")),
      node("div", "cell-detail", `结果：${attemptResultLabel(attempt.result_class)} · 错误：${text(attempt.error_class, "无")}`),
      node("div", "cell-detail", `Worker：${text(attempt.worker_id, "不可用")} · Tier ${numberText(attempt.recovery_tier)}`),
      node("div", "cell-detail full-text", `检查点：${text(attempt.checkpoint, "暂无")} · 产物：${readableValue(attempt.artifact, "暂无")}`),
    );
    return item;
  }

  function pagerSection(parent, title, note) {
    const wrapper = node("section", "section");
    wrapper.append(sectionHeading(title, note));
    const host = node("div", "pager-host");
    wrapper.append(host);
    parent.append(wrapper);
    return host;
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
    options.forEach(([value, optionLabel]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = optionLabel;
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

  function chip(label, tone) { return node("span", `status-chip ${tone || "neutral"}`, label); }
  function messageNode(message, className) { return node("div", className, message); }

  function actionSummary(item) {
    const wrapper = node("div", "list-item");
    wrapper.append(
      node("strong", "", actionTypeLabel(item.action_type)),
      node("div", "cell-detail", `${text(item.run_id, "无 run")} · ${text(item.action_id)}`),
      node("div", "full-text", text(objectValue(item.payload).summary, "暂无动作说明")),
    );
    return wrapper;
  }

  function reviewSummary(item) {
    const wrapper = node("div", "list-item");
    const accepted = objectValue(item.accepted_review);
    wrapper.append(
      node("strong", "", reviewDecisionLabel(item.decision)),
      node("div", "full-text", text(item.summary, "暂无 Reviewer 摘要")),
      node("div", "cell-detail", `请求动作：${readableValue(accepted.actions || accepted.requested_actions || item.decision, reviewDecisionLabel(item.decision))}`),
    );
    return wrapper;
  }

  function multiText(title, detail) {
    const wrapper = node("div", "cell-stack");
    wrapper.append(node("div", "cell-title", text(title)));
    if (detail) wrapper.append(node("div", "cell-detail", text(detail)));
    return wrapper;
  }

  function strongText(value) { return node("span", "cell-title", text(value)); }
  function statusText(label, tone) { return node("span", `status-text ${tone}`, label); }

  function serviceHealthLabel(value) {
    return { healthy: "正常", degraded: "降级", unavailable: "不可用", stopped: "已停止", blocked: "阻塞" }[value] || "健康状态不可用";
  }

  function serviceHealthTone(value) {
    if (value === "healthy") return "good";
    if (["blocked", "stopped", "unavailable"].includes(value)) return "bad";
    if (value === "degraded") return "warn";
    return "neutral";
  }

  function reviewDecisionLabel(value) {
    return { continue: "继续", auto_remediate: "自动整改", refocus: "重新聚焦", stop_run: "停止运行", ask_user: "请求用户决策" }[value] || "结论不可用";
  }

  function reviewStatusLabel(value) {
    return { review_complete: "审视完成", review_degraded: "Reviewer 暂时不可用", review_applying: "正在应用" }[value] || "状态不可用";
  }

  function reviewStatusTone(value) { return value === "review_complete" ? "good" : value === "review_degraded" ? "warn" : "neutral"; }
  function actionStatusLabel(value) { return { pending: "待执行", leased: "已分配", running: "执行中", completed: "已完成", failed: "失败", cancelled: "已取消" }[value] || "状态不可用"; }
  function actionStatusTone(value) { return value === "completed" ? "good" : ["failed", "cancelled"].includes(value) ? "bad" : "warn"; }
  function actionTypeLabel(value) {
    return {
      no_op: "无需操作", run_planner: "运行 Planner", run_generator: "运行 Generator",
      run_evaluator: "运行 Evaluator", run_evidence_gate: "运行证据门禁",
      run_artifact_hygiene: "运行产物清理", commit: "提交变更", push: "推送变更", cleanup: "清理运行环境",
      create_continuation: "创建续跑", restart_service: "重启服务", recover_partial_artifact: "恢复部分产物",
      recover_generator_result: "恢复 Generator 结果", run_alternate_recovery: "运行替代恢复",
      run_reviewer: "运行 Reviewer", refocus_run: "重新聚焦运行", stop_run: "停止运行", ask_user: "请求用户决策",
    }[value] || "动作不可用";
  }
  function attemptResultLabel(value) { return { success: "成功", retryable_failure: "可重试失败", recoverable_partial: "部分产物可恢复", policy_block: "策略阻塞", terminal_failure: "终止失败" }[value] || "结果不可用"; }
  function decisionStatusLabel(value) { return { open: "需要用户", closed: "已解决" }[value] || "状态不可用"; }
  function decisionStatusTone(value) { return value === "closed" ? "good" : value === "open" ? "warn" : "neutral"; }
  function freshnessLabel(value) { return { fresh: "通过", pass: "通过", stale: "过期", failed: "失败", unavailable: "不可用" }[value] || "状态不可用"; }
  function freshnessTone(value) { return ["fresh", "pass"].includes(value) ? "good" : ["failed", "unavailable"].includes(value) ? "bad" : "warn"; }
  function serviceNameLabel(value) { return { "crawler-backend": "Crawler Backend", "crawler-frontend": "Crawler Frontend", "loop-dashboard": "Loop Dashboard", "supervisor-worker": "Supervisor Worker" }[value] || text(value, "未知服务"); }

  function booleanLabel(value) {
    if (value === true) return "是";
    if (value === false) return "否";
    return "不可用";
  }

  function valueText(value) { return Number.isInteger(value) ? String(value) : "不可用"; }
  function numberText(value) { return Number.isFinite(Number(value)) ? String(Number(value)) : "不可用"; }
  function objectValue(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : {}; }

  function readableValue(value, fallback) {
    if (Array.isArray(value)) return value.length ? value.map((item) => readableValue(item, "")).join("；") : fallback;
    if (value && typeof value === "object") {
      const parts = Object.entries(value).map(([key, item]) => `${key}：${readableValue(item, "暂无")}`);
      return parts.length ? parts.join("；") : fallback;
    }
    return text(value, fallback);
  }

  function formatTime(value) {
    if (!value) return "不可用";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", { hour12: false });
  }

  function structuredDiagnosticText(value) {
    if (Array.isArray(value)) {
      const items = value.map((item) => structuredDiagnosticText(item)).filter(Boolean);
      return items.length ? items.join("；") : "暂无诊断";
    }
    if (!value || typeof value !== "object") return text(value, "暂无诊断");
    const diagnostic = value;
    const parts = [];
    if (diagnostic.status) parts.push(`状态：${text(diagnostic.status)}`);
    if (diagnostic.code) parts.push(`代码：${text(diagnostic.code)}`);
    if (diagnostic.message) parts.push(`说明：${text(diagnostic.message)}`);
    if (diagnostic.diagnostics) parts.push(`诊断：${structuredDiagnosticText(diagnostic.diagnostics)}`);
    return parts.length ? parts.join("；") : "结构化诊断不可用";
  }

  function errorText(error) {
    if (error instanceof DashboardError) {
      return error.recoveryAction ? `${error.code}：${error.message}；建议：${error.recoveryAction}` : `${error.code}：${error.message}`;
    }
    return error?.message || "请求失败";
  }

  function safeDomId(value) { return String(value || "item").replace(/[^A-Za-z0-9_-]/g, "-"); }
  function text(value, fallback = "暂无数据") { return value === null || value === undefined || value === "" ? fallback : String(value); }

  function node(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined && content !== null) element.textContent = String(content);
    return element;
  }

  window.LoopSupervisor = {
    SupervisorView, renderTable, section, sectionHeading, metrics, node, text,
    readableValue, formatTime, multiText, reviewDecisionLabel, serviceHealthLabel,
    serviceHealthTone,
  };
}());
