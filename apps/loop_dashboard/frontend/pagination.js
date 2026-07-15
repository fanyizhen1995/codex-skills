(function () {
  "use strict";

  const PAGE_SIZES = [20, 50, 100];
  const PAGE_KEYS = ["items", "next_cursor", "previous_cursor", "page_size", "total", "has_more"];
  const MAX_VISITED_PAGES = 20;
  const MAX_STORED_PAGERS = 24;
  const MAX_CURSOR_CHARS = 4096;
  const MAX_STATE_BYTES = 256 * 1024;
  const STATE_VERSION = 2;
  const DASHBOARD_STATE_PARAM = "dashboard_state";
  const DASHBOARD_STORAGE_PREFIX = "loop-dashboard-state:";
  const TOKEN_PATTERN = /^[A-Za-z0-9_-]{8,64}$/;

  class DashboardError extends Error {
    constructor(code, message, options = {}) {
      super(message || "请求失败");
      this.name = "DashboardError";
      this.code = code || "request_failed";
      this.recoveryAction = options.recoveryAction || "";
      this.httpStatus = options.httpStatus || 0;
      this.payload = options.payload || null;
    }
  }

  function structuredError(payload, httpStatus = 0) {
    if (!payload || typeof payload !== "object" || !payload.status || !payload.error) return null;
    const error = payload.error && typeof payload.error === "object" ? payload.error : {};
    return new DashboardError(
      error.code || payload.status || "request_failed",
      error.message || "请求失败",
      {
        recoveryAction: error.recovery_action || payload.recovery_action || "",
        httpStatus,
        payload,
      },
    );
  }

  function httpError(payload, response) {
    const detail = payload && payload.detail;
    const message = typeof detail === "string"
      ? detail
      : detail && typeof detail === "object"
        ? detail.message || JSON.stringify(detail)
        : `HTTP ${response.status}`;
    return new DashboardError(`http_${response.status}`, message || "请求失败", {
      httpStatus: response.status,
      payload,
    });
  }

  async function requestJson(path, options = {}) {
    const response = await fetch(path, { signal: options.signal });
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new DashboardError("invalid_json", `HTTP ${response.status}: 响应不是 JSON`, {
        httpStatus: response.status,
      });
    }
    const statusError = structuredError(payload, response.status);
    if (statusError) throw statusError;
    if (!response.ok) throw httpError(payload, response);
    return payload;
  }

  function validatePageEnvelope(payload) {
    if (!payload || typeof payload !== "object") {
      throw new DashboardError("invalid_page_envelope", "分页响应不是对象");
    }
    const keys = Object.keys(payload).sort();
    if (keys.length !== PAGE_KEYS.length || PAGE_KEYS.some((key) => !keys.includes(key))) {
      throw new DashboardError("invalid_page_envelope", "分页响应不符合 Task 7 page envelope");
    }
    if (!Array.isArray(payload.items)) {
      throw new DashboardError("invalid_page_items", "分页响应 items 不是数组");
    }
    if (!PAGE_SIZES.includes(payload.page_size)) {
      throw new DashboardError("invalid_page_size", "分页响应 page_size 无效");
    }
    if (!Number.isInteger(payload.total) || payload.total < 0) {
      throw new DashboardError("invalid_page_total", "分页响应 total 无效");
    }
    return payload;
  }

  async function fetchPage(endpoint, state, signal) {
    const url = new URL(endpoint, window.location.origin);
    const params = new URLSearchParams();
    params.set("page_size", String(state.pageSize));
    if (state.cursor) params.set("cursor", state.cursor);
    if (state.query) params.set("query", state.query);
    Object.entries(state.filters || {}).forEach(([name, value]) => {
      if (value) params.set(name, value);
    });
    url.search = params.toString();
    return validatePageEnvelope(await requestJson(url, { signal }));
  }

  function isAbortError(error) {
    return error && error.name === "AbortError";
  }

  function cloneState(state) {
    return {
      cursor: state.cursor,
      visitedCursors: [...state.visitedCursors],
      pageOffset: state.pageOffset,
      pageIndex: state.pageIndex,
      pageSize: state.pageSize,
      query: state.query,
      filters: { ...state.filters },
    };
  }

  function initialState() {
    return {
      cursor: null,
      visitedCursors: [null],
      pageOffset: 0,
      pageIndex: 0,
      pageSize: 20,
      query: "",
      filters: {},
    };
  }

  function compactToken() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID().replaceAll("-", "").substring(0, 20);
    }
    return `${Date.now().toString(36)}${Math.random().toString(36).substring(2, 14)}`;
  }

  function dashboardStorageKey(token) {
    return `${DASHBOARD_STORAGE_PREFIX}${token}`;
  }

  function emptyDashboardState() {
    return { version: STATE_VERSION, pagers: {} };
  }

  function readDashboardState(token) {
    const raw = sessionStorage.getItem(dashboardStorageKey(token));
    if (!raw || raw.length > MAX_STATE_BYTES) return emptyDashboardState();
    try {
      const payload = JSON.parse(raw);
      if (!payload || payload.version !== STATE_VERSION || !payload.pagers || typeof payload.pagers !== "object") {
        return emptyDashboardState();
      }
      const pagers = Object.fromEntries(
        Object.entries(payload.pagers)
          .filter(([key, entry]) => (
            typeof key === "string"
            && key.length > 0
            && key.length <= 240
            && entry
            && typeof entry === "object"
            && Number.isSafeInteger(entry.updatedAt)
            && entry.updatedAt >= 0
            && entry.state
            && typeof entry.state === "object"
          ))
          .sort((left, right) => right[1].updatedAt - left[1].updatedAt)
          .slice(0, MAX_STORED_PAGERS),
      );
      return { version: STATE_VERSION, pagers };
    } catch (_error) {
      return emptyDashboardState();
    }
  }

  function pruneInactiveDashboardStates(activeToken) {
    const activeKey = dashboardStorageKey(activeToken);
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key && key.startsWith(DASHBOARD_STORAGE_PREFIX) && key !== activeKey) {
        sessionStorage.removeItem(key);
      }
    }
  }

  class CursorPager {
    constructor(options) {
      this.key = options.key;
      this.endpoint = options.endpoint;
      this.container = options.container;
      this.renderItems = options.renderItems;
      this.emptyMessage = options.emptyMessage || "暂无数据";
      this.allowedFilters = options.allowedFilters || [];
      this.fixedSort = options.fixedSort || "newest";
      this.onStateChange = options.onStateChange || (() => {});
      this.stateToken = this.restoreToken();
      this.state = this.restoreState();
      this.committedState = cloneState(this.state);
      this.page = null;
      this.requestGeneration = 0;
      this.abortController = null;
      this.lastError = null;
      this.retryLastRequest = () => this.refresh();
    }

    restoreToken() {
      const params = new URLSearchParams(window.location.search);
      const token = params.get(DASHBOARD_STATE_PARAM);
      return token && TOKEN_PATTERN.test(token) ? token : compactToken();
    }

    restoreState() {
      const dashboard = readDashboardState(this.stateToken);
      const entry = dashboard.pagers[this.key];
      const payload = entry && typeof entry === "object" ? entry.state : null;
      if (!payload || typeof payload !== "object") return initialState();
      try {
        const cursors = payload.visitedCursors;
        if (
          !Array.isArray(cursors)
          || cursors.length < 1
          || cursors.length > MAX_VISITED_PAGES
          || cursors.some((cursor) => cursor !== null && (typeof cursor !== "string" || cursor.length > MAX_CURSOR_CHARS))
        ) return initialState();
        const pageOffset = Number.isSafeInteger(payload.pageOffset) && payload.pageOffset >= 0 ? payload.pageOffset : -1;
        if (
          pageOffset < 0
          || (pageOffset === 0 && cursors[0] !== null)
          || (pageOffset > 0 && (typeof cursors[0] !== "string" || !cursors[0]))
        ) return initialState();
        const pageIndex = Number.isInteger(payload.pageIndex) && payload.pageIndex >= 0 && payload.pageIndex < cursors.length
          ? payload.pageIndex
          : 0;
        const pageSize = PAGE_SIZES.includes(payload.pageSize) ? payload.pageSize : 20;
        const query = typeof payload.query === "string" ? payload.query.substring(0, 500) : "";
        const filters = {};
        if (payload.filters && typeof payload.filters === "object" && !Array.isArray(payload.filters)) {
          this.allowedFilters.forEach((name) => {
            const value = payload.filters[name];
            if (typeof value === "string" && value.length <= 500 && value) filters[name] = value;
          });
        }
        return {
          cursor: cursors[pageIndex],
          visitedCursors: [...cursors],
          pageOffset,
          pageIndex,
          pageSize,
          query,
          filters,
        };
      } catch (_error) {
        return initialState();
      }
    }

    persistState() {
      const dashboard = readDashboardState(this.stateToken);
      dashboard.pagers[this.key] = {
        updatedAt: Date.now(),
        state: cloneState(this.state),
      };
      const ordered = Object.entries(dashboard.pagers).sort(
        (left, right) => Number(right[1]?.updatedAt || 0) - Number(left[1]?.updatedAt || 0),
      );
      dashboard.pagers = Object.fromEntries(ordered.slice(0, MAX_STORED_PAGERS));
      let payload = JSON.stringify(dashboard);
      while (payload.length > MAX_STATE_BYTES && Object.keys(dashboard.pagers).length > 1) {
        const removable = Object.keys(dashboard.pagers).reverse().find((key) => key !== this.key);
        if (!removable) break;
        delete dashboard.pagers[removable];
        payload = JSON.stringify(dashboard);
      }
      if (payload.length > MAX_STATE_BYTES) {
        throw new DashboardError("pager_state_too_large", "分页状态超过本地保存上限");
      }
      pruneInactiveDashboardStates(this.stateToken);
      sessionStorage.setItem(dashboardStorageKey(this.stateToken), payload);
      const url = new URL(window.location.href);
      Array.from(url.searchParams.keys()).forEach((name) => {
        if (name.startsWith("pager.")) url.searchParams.delete(name);
      });
      url.searchParams.set(DASHBOARD_STATE_PARAM, this.stateToken);
      window.history.replaceState({}, "", url);
      this.onStateChange(cloneState(this.state));
    }

    resetCursor() {
      this.state.cursor = null;
      this.state.visitedCursors = [null];
      this.state.pageOffset = 0;
      this.state.pageIndex = 0;
    }

    async transition(mutator, retryFactory) {
      const rollbackState = cloneState(this.committedState);
      mutator();
      this.persistState();
      this.retryLastRequest = retryFactory || (() => this.refresh());
      return this.load({ rollbackState, rollbackPage: this.page });
    }

    async setPageSize(pageSize) {
      if (!PAGE_SIZES.includes(pageSize) || pageSize === this.state.pageSize) return false;
      return this.transition(
        () => {
          this.state.pageSize = pageSize;
          this.resetCursor();
        },
        () => this.setPageSize(pageSize),
      );
    }

    async setQuery(query) {
      const normalized = String(query || "").trim().substring(0, 500);
      if (normalized === this.state.query) return false;
      return this.transition(
        () => {
          this.state.query = normalized;
          this.resetCursor();
        },
        () => this.setQuery(normalized),
      );
    }

    async setFilter(name, value) {
      if (!this.allowedFilters.includes(name)) throw new DashboardError("unsupported_filter", `不支持的过滤器: ${name}`);
      const normalized = String(value || "").substring(0, 500);
      if ((this.state.filters[name] || "") === normalized) return false;
      return this.transition(
        () => {
          if (normalized) this.state.filters[name] = normalized;
          else delete this.state.filters[name];
          this.resetCursor();
        },
        () => this.setFilter(name, normalized),
      );
    }

    async goToVisited(pageIndex) {
      if (!Number.isInteger(pageIndex) || pageIndex < 0 || pageIndex >= this.state.visitedCursors.length) return false;
      return this.transition(
        () => {
          this.state.pageIndex = pageIndex;
          this.state.cursor = this.state.visitedCursors[pageIndex];
        },
        () => this.goToVisited(pageIndex),
      );
    }

    async next() {
      if (!this.page || !this.page.next_cursor) return false;
      const nextCursor = this.page.next_cursor;
      return this.transition(
        () => {
          const nextIndex = this.state.pageIndex + 1;
          this.state.visitedCursors.length = nextIndex;
          this.state.visitedCursors.push(nextCursor);
          this.state.pageIndex = nextIndex;
          if (this.state.visitedCursors.length > MAX_VISITED_PAGES) {
            this.state.visitedCursors.shift();
            this.state.pageOffset += 1;
            this.state.pageIndex -= 1;
          }
          this.state.cursor = this.state.visitedCursors[this.state.pageIndex];
        },
        () => this.next(),
      );
    }

    async refresh() {
      return this.load({ rollbackState: cloneState(this.committedState), rollbackPage: this.page });
    }

    destroy() {
      this.requestGeneration += 1;
      if (this.abortController) this.abortController.abort();
      this.abortController = null;
    }

    async load(options = {}) {
      const generation = ++this.requestGeneration;
      if (this.abortController) this.abortController.abort();
      this.abortController = new AbortController();
      const requestedState = cloneState(this.state);
      const rollbackState = options.rollbackState || cloneState(this.committedState);
      const rollbackPage = options.rollbackPage === undefined ? this.page : options.rollbackPage;
      if (!this.page) this.container.replaceChildren(messageNode("正在读取...", "empty-state"));
      else this.container.setAttribute("aria-busy", "true");
      try {
        const page = await fetchPage(this.endpoint, requestedState, this.abortController.signal);
        if (generation !== this.requestGeneration) return false;
        this.page = page;
        this.state = requestedState;
        this.committedState = cloneState(requestedState);
        this.lastError = null;
        this.persistState();
        this.render();
        return true;
      } catch (error) {
        if (isAbortError(error) || generation !== this.requestGeneration) return false;
        this.state = cloneState(rollbackState);
        this.committedState = cloneState(rollbackState);
        this.page = rollbackPage;
        this.lastError = error instanceof DashboardError
          ? error
          : new DashboardError("request_failed", error.message || "分页请求失败");
        this.persistState();
        this.render();
        return false;
      } finally {
        if (generation === this.requestGeneration) {
          this.container.removeAttribute("aria-busy");
          this.abortController = null;
        }
      }
    }

    render() {
      const fragment = document.createDocumentFragment();
      if (this.lastError) fragment.append(this.renderError());
      if (this.page) {
        const content = document.createElement("div");
        content.className = "paged-content";
        if (this.page.items.length) this.renderItems(content, this.page.items, this.page);
        else content.append(messageNode(this.emptyMessage, "empty-state"));
        fragment.append(content, this.renderPager());
      } else if (!this.lastError) {
        fragment.append(messageNode(this.emptyMessage, "empty-state"));
      }
      this.container.replaceChildren(fragment);
    }

    renderError() {
      const wrapper = messageNode("", "error-state pager-error");
      const detail = this.lastError.recoveryAction
        ? `${this.lastError.code}：${this.lastError.message}；建议：${this.lastError.recoveryAction}`
        : `${this.lastError.code}：${this.lastError.message}`;
      wrapper.append(document.createTextNode(detail));
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "page-button";
      retry.textContent = "重试";
      retry.addEventListener("click", () => this.retryLastRequest());
      wrapper.append(retry);
      return wrapper;
    }

    renderPager() {
      const pager = document.createElement("div");
      pager.className = "pager";
      pager.dataset.pagerKey = this.key;
      const absolutePage = this.state.pageOffset + this.state.pageIndex;
      const start = this.page.total === 0 ? 0 : absolutePage * this.page.page_size + 1;
      const end = this.page.total === 0 ? 0 : Math.min(start + this.page.items.length - 1, this.page.total);
      const summary = document.createElement("span");
      summary.className = "pager-summary";
      summary.append(document.createTextNode(`第 ${start}-${end} 条，共 ${this.page.total} 条 · 每页 `));
      const pageSize = document.createElement("select");
      pageSize.className = "control page-size";
      pageSize.setAttribute("aria-label", "每页条数");
      PAGE_SIZES.forEach((size) => {
        const option = document.createElement("option");
        option.value = String(size);
        option.textContent = String(size);
        option.selected = size === this.state.pageSize;
        pageSize.append(option);
      });
      pageSize.addEventListener("change", () => this.setPageSize(Number(pageSize.value)));
      summary.append(pageSize, document.createTextNode(` · 排序：${this.fixedSort === "newest" ? "最新优先" : "固定顺序"}`));

      const actions = document.createElement("div");
      actions.className = "pager-actions";
      actions.append(this.pageButton("上一页", this.state.pageIndex === 0, () => this.goToVisited(this.state.pageIndex - 1)));
      this.state.visitedCursors.map((_cursor, index) => {
        const label = String(this.state.pageOffset + index + 1);
        const button = this.pageButton(label, false, () => this.goToVisited(index));
        if (index === this.state.pageIndex) {
          button.classList.add("is-active");
          button.setAttribute("aria-current", "page");
        }
        actions.append(button);
        return button;
      });
      actions.append(this.pageButton("下一页", !this.page.next_cursor, () => this.next()));
      pager.append(summary, actions);
      return pager;
    }

    pageButton(label, disabled, action) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "page-button";
      button.textContent = label;
      button.disabled = disabled;
      button.addEventListener("click", action);
      return button;
    }
  }

  function messageNode(message, className) {
    const node = document.createElement("div");
    node.className = className;
    node.textContent = message;
    return node;
  }

  window.LoopPagination = {
    CursorPager,
    DashboardError,
    PAGE_SIZES,
    fetchPage,
    requestJson,
    structuredError,
    validatePageEnvelope,
  };
}());
