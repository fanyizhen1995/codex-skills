import { Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getSources, runSource } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { SourceProfile, Status } from "../types";

function groupKey(source: SourceProfile) {
  return `${source.type} / ${source.target_domain}`;
}

function statusForSources(sources: SourceProfile[], error: string): Status {
  if (error) {
    return "failed";
  }
  if (sources.some((source) => source.auth_required && source.auth_state !== "ready")) {
    return "needs_auth_config";
  }
  return "trusted";
}

function timeLabel(value?: string) {
  if (!value) {
    return "未运行";
  }
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function SourcesPage() {
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [runningSource, setRunningSource] = useState("");

  async function loadSources() {
    setLoading(true);
    try {
      const response = await getSources();
      setSources(response);
      setError("");
      return response;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载来源订阅失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSources();
  }, []);

  const groupedSources = useMemo(
    () =>
      sources.reduce<Record<string, SourceProfile[]>>((groups, source) => {
        const key = groupKey(source);
        groups[key] = [...(groups[key] ?? []), source];
        return groups;
      }, {}),
    [sources]
  );

  async function handleRun(source: SourceProfile) {
    setRunningSource(source.id);
    setNotice("");
    setError("");
    try {
      const response = await runSource(source.id);
      const refreshed = await loadSources();
      if (refreshed !== null) {
        setNotice(`${source.name} 运行已提交：${response.status}`);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "运行来源失败");
    } finally {
      setRunningSource("");
    }
  }

  return (
    <section className="page-section" aria-labelledby="sources-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">订阅与抓取</p>
          <h1 id="sources-title">来源订阅</h1>
        </div>
        <StatusBadge status={statusForSources(sources, error)} />
      </div>

      {(error || notice) && <small role="status">{error || notice}</small>}

      <div className="source-groups">
        {sources.length === 0 ? (
          <div className="work-panel">
            <h2>来源列表</h2>
            <div className="empty-state">{loading ? "正在加载来源订阅" : "暂无来源订阅"}</div>
          </div>
        ) : (
          Object.entries(groupedSources).map(([group, items]) => (
            <div className="work-panel" key={group}>
              <h2>{group}</h2>
              <div className="responsive-table" role="table" aria-label={`${group} 来源`}>
                <div className="table-row table-head" role="row">
                  <span role="columnheader">来源</span>
                  <span role="columnheader">信任</span>
                  <span role="columnheader">计划</span>
                  <span role="columnheader">认证</span>
                  <span role="columnheader">上次运行</span>
                  <span role="columnheader">操作</span>
                </div>
                {items.map((source) => (
                  <div className="table-row" role="row" key={source.id}>
                    <span role="cell">
                      <strong>{source.name}</strong>
                      <small>{source.url}</small>
                    </span>
                    <span role="cell">{source.trust_level}</span>
                    <span role="cell">{source.schedule || "未配置"}</span>
                    <span role="cell">{source.auth_required ? source.auth_state : "无需认证"}</span>
                    <span role="cell">
                      {timeLabel(source.last_run_at)}
                      <small>{source.last_run_status ?? "暂无状态"}</small>
                    </span>
                    <span role="cell">
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`运行 ${source.name}`}
                        onClick={() => handleRun(source)}
                        disabled={runningSource === source.id || !source.enabled}
                      >
                        <Play aria-hidden="true" size={16} />
                        {runningSource === source.id ? "运行中" : "运行"}
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
