import { Check, Play, RefreshCw, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { acceptAcceleratorCandidate, getAcceleratorCandidates, getSources, rejectAcceleratorCandidate, runSource } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { AcceleratorCandidate, SourceProfile, Status } from "../types";

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

function runPolicyLabel(source: SourceProfile) {
  return source.run_policy === "once" ? "一次性" : "定时";
}

function acceptPayload(candidate: AcceleratorCandidate) {
  return {
    source_id: `compute-accelerators-${candidate.vendor}-${candidate.normalized_model}`.toLowerCase(),
    name: `${candidate.vendor} ${candidate.model_name} accelerator specs`,
    url: candidate.evidence_url || candidate.source_url,
    scope: [candidate.scope],
    source_rank: "S1"
  };
}

export function SourcesPage() {
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [candidates, setCandidates] = useState<AcceleratorCandidate[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [runningSource, setRunningSource] = useState("");
  const [reviewingCandidate, setReviewingCandidate] = useState<number | null>(null);

  async function loadSources() {
    setLoading(true);
    try {
      const [response, candidateResponse] = await Promise.all([getSources(), getAcceleratorCandidates()]);
      setSources(response);
      setCandidates(candidateResponse.filter((candidate) => candidate.status === "pending"));
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

  async function handleAccept(candidate: AcceleratorCandidate) {
    setReviewingCandidate(candidate.id);
    setNotice("");
    setError("");
    try {
      await acceptAcceleratorCandidate(candidate.id, acceptPayload(candidate));
      setCandidates((currentCandidates) => currentCandidates.filter((item) => item.id !== candidate.id));
      setNotice(`${candidate.model_name} 已接受为来源`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "接受候选失败");
      setReviewingCandidate(null);
      return;
    }
    const refreshed = await loadSources();
    if (refreshed === null) {
      setError("候选已接受，刷新来源失败");
    }
    setReviewingCandidate(null);
  }

  async function handleReject(candidate: AcceleratorCandidate) {
    setReviewingCandidate(candidate.id);
    setNotice("");
    setError("");
    try {
      await rejectAcceleratorCandidate(candidate.id);
      setCandidates((currentCandidates) => currentCandidates.filter((item) => item.id !== candidate.id));
      setNotice(`${candidate.model_name} 已拒绝`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "拒绝候选失败");
      setReviewingCandidate(null);
      return;
    }
    const refreshed = await loadSources();
    if (refreshed === null) {
      setError("候选已拒绝，刷新来源失败");
    }
    setReviewingCandidate(null);
  }

  return (
    <section className="page-section" aria-labelledby="sources-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">订阅与抓取</p>
          <h1 id="sources-title">来源订阅</h1>
        </div>
        <div className="inline-actions">
          <button className="icon-button" type="button" onClick={() => loadSources()} disabled={loading}>
            <RefreshCw aria-hidden="true" size={16} />
            刷新来源
          </button>
          <StatusBadge status={statusForSources(sources, error)} />
        </div>
      </div>

      {(error || notice) && <small role="status">{error || notice}</small>}

      <div className="source-groups">
        <div className="work-panel">
          <h2>新硬件候选</h2>
          {candidates.length === 0 ? (
            <div className="empty-state">{loading ? "正在加载候选" : "暂无新硬件候选"}</div>
          ) : (
            <div className="responsive-table" role="table" aria-label="新硬件候选">
              <div className="table-row table-head" role="row">
                <span role="columnheader">型号</span>
                <span role="columnheader">证据</span>
                <span role="columnheader">来源</span>
                <span role="columnheader">操作</span>
              </div>
              {candidates.map((candidate) => (
                <div className="table-row" role="row" key={candidate.id}>
                  <span role="cell">
                    <strong>{candidate.model_name}</strong>
                    <small>
                      {candidate.vendor} · {candidate.scope} · {(candidate.confidence * 100).toFixed(0)}%
                    </small>
                  </span>
                  <span role="cell">
                    {candidate.evidence_text}
                    <small>{candidate.evidence_url || candidate.source_url}</small>
                  </span>
                  <span role="cell">{candidate.source_profile_id}</span>
                  <span role="cell">
                    <div className="inline-actions">
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`接受 ${candidate.model_name}`}
                        onClick={() => handleAccept(candidate)}
                        disabled={reviewingCandidate === candidate.id}
                      >
                        <Check aria-hidden="true" size={16} />
                        接受
                      </button>
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`拒绝 ${candidate.model_name}`}
                        onClick={() => handleReject(candidate)}
                        disabled={reviewingCandidate === candidate.id}
                      >
                        <X aria-hidden="true" size={16} />
                        拒绝
                      </button>
                    </div>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

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
                    <span role="cell">
                      {source.schedule || "未配置"}
                      <small>{runPolicyLabel(source)}</small>
                    </span>
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
