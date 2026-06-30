import { Check, Play, RefreshCw, ShieldCheck, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  acceptAcceleratorCandidate,
  createManualIngest,
  getAcceleratorCandidates,
  getSources,
  rejectAcceleratorCandidate,
  runSource,
  trustAcceleratorCandidateSource
} from "../api";
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

function manualIngestReasonLabel(reason?: string | null, status?: string) {
  if (reason === "waiting for clean git baseline before automatic retry") {
    return "等待工作区清理后自动重试";
  }
  return reason ?? status ?? "未知状态";
}

export function SourcesPage() {
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [candidates, setCandidates] = useState<AcceleratorCandidate[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [runningSource, setRunningSource] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [manualDomain, setManualDomain] = useState("ai_infra");
  const [manualAutoCommit, setManualAutoCommit] = useState(true);
  const [manualRunning, setManualRunning] = useState(false);
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

  async function handleManualIngest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const url = manualUrl.trim();
    const domain = manualDomain.trim() || "ai_infra";
    if (!url) {
      setNotice("");
      setError("请输入入库 URL");
      return;
    }
    setManualRunning(true);
    setNotice("");
    setError("");
    try {
      const result = await createManualIngest({
        url,
        domain,
        auto_commit_enabled: manualAutoCommit
      });
      await loadSources();
      if (result.status === "succeeded") {
        const taskText = result.task_id ? `任务 #${result.task_id}` : "未生成任务";
        const commitText = result.commit_sha ? `，commit ${result.commit_sha.slice(0, 12)}` : "";
        setNotice(`已入库并提交：${taskText}${commitText}`);
        setManualUrl("");
      } else if (result.status === "skipped") {
        setNotice(`未发现新内容：${result.url}`);
      } else {
        const taskText = result.task_id ? `任务 #${result.task_id}` : "未生成任务";
        setNotice(`入库未完成：${taskText} · ${manualIngestReasonLabel(result.reason, result.status)}`);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "URL 入库失败");
    } finally {
      setManualRunning(false);
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

  async function handleTrustCandidateSource(candidate: AcceleratorCandidate) {
    setReviewingCandidate(candidate.id);
    setNotice("");
    setError("");
    try {
      const result = await trustAcceleratorCandidateSource(candidate.id);
      setCandidates((currentCandidates) => currentCandidates.filter((item) => !result.candidate_ids.includes(item.id)));
      setNotice(`已信任 ${result.domain}，同站接受 ${result.accepted_count} 个候选`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "信任同站候选失败");
      setReviewingCandidate(null);
      return;
    }
    const refreshed = await loadSources();
    if (refreshed === null) {
      setError("候选已信任，刷新来源失败");
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
        <div className="work-panel manual-ingest-panel">
          <h2>零散 URL 入库</h2>
          <form className="manual-ingest-form" onSubmit={handleManualIngest}>
            <label className="field-row manual-url-field">
              <span>入库 URL</span>
              <input
                aria-label="入库 URL"
                placeholder="https://example.com/doc"
                type="text"
                value={manualUrl}
                onChange={(event) => setManualUrl(event.target.value)}
              />
            </label>
            <label className="field-row manual-domain-field">
              <span>领域</span>
              <input
                aria-label="入库领域"
                value={manualDomain}
                onChange={(event) => setManualDomain(event.target.value)}
              />
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={manualAutoCommit}
                onChange={(event) => setManualAutoCommit(event.target.checked)}
              />
              自动提交
            </label>
            <button className="icon-button" type="submit" disabled={manualRunning}>
              <Play aria-hidden="true" size={16} />
              {manualRunning ? "入库中" : "抓取并入库"}
            </button>
          </form>
        </div>

        <div className="work-panel">
          <h2>新硬件候选</h2>
          {candidates.length === 0 ? (
            <div className="empty-state">{loading ? "正在加载候选" : "暂无新硬件候选"}</div>
          ) : (
            <div className="responsive-table candidate-table" role="table" aria-label="新硬件候选">
              <div className="table-row table-head candidate-row" role="row">
                <span role="columnheader">型号</span>
                <span role="columnheader">证据</span>
                <span role="columnheader">来源</span>
                <span role="columnheader">操作</span>
              </div>
              {candidates.map((candidate) => (
                <div className="table-row candidate-row" role="row" key={candidate.id}>
                  <span role="cell">
                    <strong>{candidate.model_name}</strong>
                    <small>
                      {candidate.vendor} · {candidate.scope} · {(candidate.confidence * 100).toFixed(0)}%
                    </small>
                  </span>
                  <span role="cell">
                    <span className="candidate-evidence-text" title={candidate.evidence_text}>
                      {candidate.evidence_text}
                    </span>
                    <small className="candidate-evidence-url" title={candidate.evidence_url || candidate.source_url}>
                      {candidate.evidence_url || candidate.source_url}
                    </small>
                  </span>
                  <span className="candidate-source-id" role="cell" title={candidate.source_profile_id}>
                    {candidate.source_profile_id}
                  </span>
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
                        aria-label={`信任同站 ${candidate.model_name}`}
                        onClick={() => handleTrustCandidateSource(candidate)}
                        disabled={reviewingCandidate === candidate.id}
                      >
                        <ShieldCheck aria-hidden="true" size={16} />
                        同站
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
