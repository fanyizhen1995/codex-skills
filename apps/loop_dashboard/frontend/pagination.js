(function () {
  "use strict";

  const PAGE_SIZES = [20, 50, 100];
  const PAGE_KEYS = ["items", "next_cursor", "previous_cursor", "page_size", "total", "has_more"];

  function encodeHistory(value) {
    return btoa(JSON.stringify(value)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  }

  function decodeHistory(value) {
    if (!value) return null;
    try {
      const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
      return JSON.parse(atob(normalized + "=".repeat((4 - normalized.length % 4) % 4)));
    } catch (_error) {
      return null;
    }
  }

  function validatePageEnvelope(payload) {
    if (payload && payload.status === "capacity_exceeded") {
      const message = payload.error?.message || "分页快照容量已满";
      throw new Error(`capacity_exceeded: ${message}`);
    }
    if (payload && payload.status && payload.error) {
      const code = payload.error.code || payload.status || "unavailable";
      const message = payload.error.message || "分页数据不可用";
      throw new Error(`${code}: ${message}`);
    }
    if (!payload || typeof payload !== "object") throw new Error("分页响应不是对象");
    const keys = Object.keys(payload).sort();
    if (keys.length !== PAGE_KEYS.length || PAGE_KEYS.some((key) => !keys.includes(key))) {
      throw new Error("分页响应不符合 Task 7 page envelope");
    }
    if (!Array.isArray(payload.items)) throw new Error("分页响应 items 不是数组");
    if (!PAGE_SIZES.includes(payload.page_size)) throw new Error("分页响应 page_size 无效");
    if (!Number.isInteger(payload.total) || payload.total < 0) throw new Error("分页响应 total 无效");
    return payload;
  }

  async function fetchPage(endpoint, state) {
    const url = new URL(endpoint, window.location.origin);
    const params = new URLSearchParams();
    params.set("page_size", String(state.pageSize));
    if (state.cursor) params.set("cursor", state.cursor);
    if (state.query) params.set("query", state.query);
    Object.entries(state.filters || {}).forEach(([name, value]) => {
      if (value) params.set(name, value);
    });
    url.search = params.toString();
    const response = await fetch(url);
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error(`HTTP ${response.status}: 响应不是 JSON`);
    }
    if (!response.ok) {
      const detail = payload && (payload.detail || payload.error?.message || payload.status);
      throw new Error(`HTTP ${response.status}: ${detail || "请求失败"}`);
    }
    return validatePageEnvelope(payload);
  }

  class CursorPager {
    constructor(options) {
      this.key = options.key;
      this.endpoint = options.endpoint;
      this.container = options.container;
      this.renderItems = options.renderItems;
      this.emptyMessage = options.emptyMessage || "暂无数据";
      this.allowedFilters = options.allowedFilters || [];
      this.onStateChange = options.onStateChange || (() => {});
      this.state = this.restoreState();
      this.page = null;
      this.loading = false;
    }

    param(name) {
      return `pager.${this.key}.${name}`;
    }

    restoreState() {
      const params = new URLSearchParams(window.location.search);
      const stored = decodeHistory(params.get(this.param("history")))
        || decodeHistory(sessionStorage.getItem(this.param("history")));
      const visitedCursors = Array.isArray(stored) && stored.length && stored[0] === null
        ? stored.filter((cursor) => cursor === null || typeof cursor === "string")
        : [null];
      const requestedIndex = Number.parseInt(params.get(this.param("page")) || "1", 10) - 1;
      const pageIndex = Number.isInteger(requestedIndex) && requestedIndex >= 0 && requestedIndex < visitedCursors.length
        ? requestedIndex
        : 0;
      const requestedSize = Number.parseInt(params.get(this.param("size")) || "20", 10);
      const filters = {};
      this.allowedFilters.forEach((name) => {
        const value = params.get(this.param(`filter.${name}`));
        if (value) filters[name] = value;
      });
      return {
        cursor: visitedCursors[pageIndex],
        visitedCursors,
        pageIndex,
        pageSize: PAGE_SIZES.includes(requestedSize) ? requestedSize : 20,
        query: params.get(this.param("query")) || "",
        sort: params.get(this.param("sort")) || "newest",
        filters,
      };
    }

    persistState() {
      const url = new URL(window.location.href);
      const history = encodeHistory(this.state.visitedCursors);
      url.searchParams.set(this.param("page"), String(this.state.pageIndex + 1));
      url.searchParams.set(this.param("size"), String(this.state.pageSize));
      url.searchParams.set(this.param("sort"), this.state.sort);
      url.searchParams.set(this.param("history"), history);
      if (this.state.query) url.searchParams.set(this.param("query"), this.state.query);
      else url.searchParams.delete(this.param("query"));
      this.allowedFilters.forEach((name) => {
        const param = this.param(`filter.${name}`);
        if (this.state.filters[name]) url.searchParams.set(param, this.state.filters[name]);
        else url.searchParams.delete(param);
      });
      sessionStorage.setItem(this.param("history"), history);
      window.history.replaceState({}, "", url);
      this.onStateChange(this.state);
    }

    resetCursor() {
      this.state.cursor = null;
      this.state.visitedCursors = [null];
      this.state.pageIndex = 0;
    }

    async setPageSize(pageSize) {
      if (!PAGE_SIZES.includes(pageSize) || pageSize === this.state.pageSize) return;
      this.state.pageSize = pageSize;
      this.resetCursor();
      this.persistState();
      await this.load();
    }

    async setQuery(query) {
      const normalized = String(query || "").trim();
      if (normalized === this.state.query) return;
      this.state.query = normalized;
      this.resetCursor();
      this.persistState();
      await this.load();
    }

    async setFilter(name, value) {
      if (!this.allowedFilters.includes(name)) throw new Error(`不支持的过滤器: ${name}`);
      const normalized = String(value || "");
      if ((this.state.filters[name] || "") === normalized) return;
      if (normalized) this.state.filters[name] = normalized;
      else delete this.state.filters[name];
      this.resetCursor();
      this.persistState();
      await this.load();
    }

    async goToVisited(pageIndex) {
      if (!Number.isInteger(pageIndex) || pageIndex < 0 || pageIndex >= this.state.visitedCursors.length) return;
      this.state.pageIndex = pageIndex;
      this.state.cursor = this.state.visitedCursors[pageIndex];
      this.persistState();
      await this.load();
    }

    async next() {
      if (!this.page || !this.page.next_cursor) return;
      const nextIndex = this.state.pageIndex + 1;
      if (nextIndex === this.state.visitedCursors.length) {
        this.state.visitedCursors.push(this.page.next_cursor);
      } else {
        this.state.visitedCursors[nextIndex] = this.page.next_cursor;
        this.state.visitedCursors.length = nextIndex + 1;
      }
      this.state.pageIndex = nextIndex;
      this.state.cursor = this.state.visitedCursors[nextIndex];
      this.persistState();
      await this.load();
    }

    async load() {
      if (this.loading) return;
      this.loading = true;
      this.container.replaceChildren(messageNode("正在读取...", "empty-state"));
      try {
        this.page = await fetchPage(this.endpoint, this.state);
        this.render();
      } catch (error) {
        this.page = null;
        this.container.replaceChildren(messageNode(error.message || "分页数据不可用", "error-state"));
      } finally {
        this.loading = false;
      }
    }

    render() {
      const fragment = document.createDocumentFragment();
      const items = this.page.items;
      const content = document.createElement("div");
      content.className = "paged-content";
      if (items.length) this.renderItems(content, items, this.page);
      else content.append(messageNode(this.emptyMessage, "empty-state"));
      fragment.append(content, this.renderPager());
      this.container.replaceChildren(fragment);
    }

    renderPager() {
      const pager = document.createElement("div");
      pager.className = "pager";
      pager.dataset.pagerKey = this.key;
      const start = this.page.total === 0 ? 0 : this.state.pageIndex * this.page.page_size + 1;
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
      summary.append(pageSize);

      const actions = document.createElement("div");
      actions.className = "pager-actions";
      actions.append(this.pageButton("上一页", this.state.pageIndex === 0, () => this.goToVisited(this.state.pageIndex - 1)));
      this.state.visitedCursors.map((_cursor, index) => {
        const button = this.pageButton(String(index + 1), false, () => this.goToVisited(index));
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

  window.LoopPagination = { CursorPager, PAGE_SIZES, fetchPage, validatePageEnvelope };
}());
