import { RefreshCw, Search, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { askCodex, getDomains, getGraph, getJob, rebuildSearch, searchWiki } from "../api";
import { WikiGraph } from "../components/WikiGraph";
import { StatusBadge } from "../components/StatusBadge";
import type { CodexJob, Domain, SearchResult, WikiGraphResponse } from "../types";

function resultDescription(result: SearchResult) {
  return result.description ?? result.snippet ?? "暂无摘要";
}

function jobAnswer(job: CodexJob | null) {
  if (!job) {
    return "尚未发起查询。";
  }
  return job.answer ?? job.stdout ?? job.error ?? job.stderr ?? `任务状态：${job.status}`;
}

function jobCitations(job: CodexJob | null, results: SearchResult[]) {
  const citations = job?.cited_paths ?? job?.citations;
  if (citations && citations.length > 0) {
    return citations;
  }
  return results.slice(0, 3).map((result) => result.path);
}

export function KnowledgePage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domain, setDomain] = useState("");
  const [query, setQuery] = useState("");
  const [question, setQuestion] = useState("");
  const [persist, setPersist] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [graph, setGraph] = useState<WikiGraphResponse>({ nodes: [], edges: [] });
  const [jobId, setJobId] = useState<number | null>(null);
  const [job, setJob] = useState<CodexJob | null>(null);
  const [message, setMessage] = useState("");
  const [domainsLoading, setDomainsLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [asking, setAsking] = useState(false);

  const citations = useMemo(() => jobCitations(job, results), [job, results]);
  const relatedPages = job?.related_pages ?? results.slice(0, 4);
  const hasDomains = domains.length > 0 && domain !== "";
  const actionsDisabled = !hasDomains || domainsLoading;

  useEffect(() => {
    let cancelled = false;

    getDomains()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setDomains(response);
        setDomain(response[0]?.id ?? "");
        setMessage(response.length === 0 ? "未发现可用 wiki domain，无法执行知识查询。" : "");
      })
      .catch((error) => {
        if (!cancelled) {
          setDomains([]);
          setDomain("");
          setMessage(error instanceof Error ? error.message : "加载 wiki domain 失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDomainsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!domain) {
      return undefined;
    }

    let cancelled = false;

    getGraph(domain)
      .then((response) => {
        if (!cancelled) {
          setGraph({
            nodes: response.nodes ?? [],
            edges: response.edges ?? []
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGraph({ nodes: [], edges: [] });
          setMessage("加载知识关系图失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [domain]);

  useEffect(() => {
    if (jobId === null) {
      return undefined;
    }

    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const nextJob = await getJob(jobId);
        if (cancelled) {
          return;
        }
        setJob(nextJob);
        if (nextJob.status === "pending" || nextJob.status === "running") {
          timer = window.setTimeout(poll, 1500);
        }
      } catch (error) {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : "查询任务状态失败");
        }
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [jobId]);

  async function handleSearch() {
    if (!hasDomains) {
      setMessage("未发现可用 wiki domain，无法执行搜索。");
      return;
    }

    const trimmed = query.trim();
    if (!trimmed) {
      setMessage("请输入搜索关键词。");
      return;
    }

    setSearching(true);
    setMessage("");
    try {
      const nextResults = await searchWiki(trimmed, domain);
      setResults(nextResults);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  }

  async function handleAsk() {
    if (!hasDomains) {
      setMessage("未发现可用 wiki domain，无法执行 Codex 查询。");
      return;
    }

    const trimmed = question.trim();
    if (!trimmed) {
      setMessage("请输入 Codex 问题。");
      return;
    }

    setAsking(true);
    setMessage("");
    try {
      const response = await askCodex(domain, trimmed, persist);
      setJob({ status: "pending", job_id: response.job_id, question: trimmed });
      setJobId(response.job_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Codex 查询失败");
    } finally {
      setAsking(false);
    }
  }

  async function handleRebuild() {
    if (!hasDomains) {
      setMessage("未发现可用 wiki domain，无法重建索引。");
      return;
    }

    setMessage("");
    try {
      const response = await rebuildSearch(domain);
      setMessage(`已重建索引：${response.indexed} 条`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "重建索引失败");
    }
  }

  return (
    <section className="page-section" aria-labelledby="knowledge-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">检索与问答</p>
          <h1 id="knowledge-title">知识工作台</h1>
        </div>
        <StatusBadge status={job?.status === "failed" ? "failed" : "trusted"} />
      </div>

      <div className="work-panel">
        <div style={{ display: "grid", gap: 12 }}>
          <label style={{ display: "grid", gap: 6, maxWidth: 260 }}>
            <span className="metric-label">Domain</span>
            <select aria-label="Domain" value={domain} onChange={(event) => setDomain(event.target.value)} disabled={!hasDomains}>
              {domains.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          {!domainsLoading && !hasDomains && <small role="status">未发现可用 wiki domain，无法执行知识查询。</small>}

          <div style={{ display: "grid", gap: 8 }}>
            <h2>全文搜索</h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <input
                aria-label="全文搜索关键词"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="输入关键词、路径或主题"
                style={{ minHeight: 34, minWidth: 260, flex: "1 1 280px" }}
              />
              <button className="icon-button" type="button" onClick={handleSearch} disabled={searching || actionsDisabled}>
                <Search aria-hidden="true" size={16} />
                {searching ? "搜索中" : "搜索"}
              </button>
              <button className="icon-button" type="button" onClick={handleRebuild} disabled={actionsDisabled}>
                <RefreshCw aria-hidden="true" size={16} />
                重建索引
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gap: 8 }}>
            <h2>Codex 查询</h2>
            <textarea
              aria-label="Codex 查询问题"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="向 Codex 询问当前 domain 的知识问题"
              rows={4}
            />
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={persist} onChange={(event) => setPersist(event.target.checked)} />
              有长期价值时沉淀进 curated wiki
            </label>
            <button
              className="icon-button"
              type="button"
              onClick={handleAsk}
              disabled={asking || actionsDisabled}
              style={{ width: "fit-content" }}
            >
              <Send aria-hidden="true" size={16} />
              {asking ? "提交中" : "提问"}
            </button>
          </div>

          {message && <small role="status">{message}</small>}
        </div>
      </div>

      <div className="panel-grid">
        <div className="work-panel">
          <h2>搜索结果</h2>
          <div className="compact-list">
            {results.length === 0 ? (
              <small>暂无结果</small>
            ) : (
              results.map((result) => (
                <div className="list-row" key={`${result.domain ?? domain}-${result.path}`}>
                  <span>
                    <strong>{result.title ?? result.path}</strong>
                    <small>{result.path}</small>
                    <small>{resultDescription(result)}</small>
                  </span>
                  {typeof result.score === "number" && <small>{result.score.toFixed(2)}</small>}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="work-panel">
          <h2>回答</h2>
          <p>{jobAnswer(job)}</p>
          {job?.status && <small>状态：{job.status}</small>}
        </div>

        <div className="work-panel">
          <h2>引用路径</h2>
          <ul className="plain-list">
            {citations.length === 0 ? <li>暂无引用</li> : citations.map((path) => <li key={path}>{path}</li>)}
          </ul>
        </div>

        <div className="work-panel">
          <h2>相关 wiki 页面</h2>
          <ul className="plain-list">
            {relatedPages.length === 0 ? (
              <li>暂无相关页面</li>
            ) : (
              relatedPages.map((page) => <li key={page.path}>{page.title ?? page.path}</li>)
            )}
          </ul>
        </div>

        <div className="work-panel chart-panel">
          <h2>知识关系图</h2>
          <WikiGraph nodes={graph.nodes} edges={graph.edges} />
        </div>

        <div className="work-panel chart-panel">
          <h2>主题时间线</h2>
          <div className="chart-frame">
            <div className="empty-state">暂无主题时间线数据</div>
          </div>
        </div>
      </div>
    </section>
  );
}
