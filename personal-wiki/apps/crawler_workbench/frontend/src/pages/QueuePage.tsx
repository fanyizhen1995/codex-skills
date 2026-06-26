import { Check, ChevronDown, ChevronRight, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";

import { approveTask, getQueue, rejectTask, trustQueueSource } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { IngestTask, Status } from "../types";

function queueStatus(tasks: IngestTask[], error: string): Status {
  if (error) {
    return "failed";
  }
  if (tasks.some((task) => task.status === "running")) {
    return "running";
  }
  if (tasks.some((task) => task.status === "failed")) {
    return "failed";
  }
  if (tasks.some((task) => task.status === "pending")) {
    return "pending";
  }
  return "ready";
}

function shouldShowInManualQueue(task: IngestTask) {
  return task.status === "pending" || task.status === "running" || task.status === "failed";
}

export function QueuePage() {
  const [tasks, setTasks] = useState<IngestTask[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [expandedTaskIds, setExpandedTaskIds] = useState<Set<number>>(new Set());
  const [trustTaskId, setTrustTaskId] = useState<number | null>(null);
  const [trustMode, setTrustMode] = useState<"manual" | "scheduled">("manual");
  const [trustFrequency, setTrustFrequency] = useState<"daily" | "weekly" | "monthly">("weekly");

  async function loadQueue() {
    setLoading(true);
    try {
      const response = await getQueue();
      setTasks(response);
      setError("");
      return response;
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载入库队列失败");
      return null;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  async function handleApprove(task: IngestTask) {
    setActiveTaskId(task.id);
    setNotice("");
    setError("");
    try {
      await approveTask(task.id);
      const refreshed = await loadQueue();
      if (refreshed !== null) {
        setNotice(`任务 #${task.id} 已通过`);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "通过任务失败");
    } finally {
      setActiveTaskId(null);
    }
  }

  async function handleReject(task: IngestTask) {
    setActiveTaskId(task.id);
    setNotice("");
    setError("");
    try {
      await rejectTask(task.id, "前端手动拒绝");
      const refreshed = await loadQueue();
      if (refreshed !== null) {
        setNotice(`任务 #${task.id} 已拒绝`);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "拒绝任务失败");
    } finally {
      setActiveTaskId(null);
    }
  }

  function toggleDetails(taskId: number) {
    setExpandedTaskIds((current) => {
      const next = new Set(current);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }

  function openTrustPanel(taskId: number) {
    setTrustTaskId((current) => (current === taskId ? null : taskId));
    setTrustMode("manual");
    setTrustFrequency("weekly");
    setNotice("");
    setError("");
  }

  async function handleTrustSource(task: IngestTask) {
    setActiveTaskId(task.id);
    setNotice("");
    setError("");
    try {
      const result = await trustQueueSource(task.id, {
        mode: trustMode,
        ...(trustMode === "scheduled" ? { frequency: trustFrequency } : {})
      });
      const refreshed = await loadQueue();
      if (refreshed !== null) {
        setTrustTaskId(null);
        const domain = typeof result.domain === "string" ? result.domain : "该网站";
        const approvedCount = typeof result.approved_count === "number" ? result.approved_count : 0;
        setNotice(`已将 ${domain} 设为信源，已通过 ${approvedCount} 条同站点任务`);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "设为信源失败");
    } finally {
      setActiveTaskId(null);
    }
  }

  const manualTasks = tasks.filter(shouldShowInManualQueue);
  const approvedCount = tasks.filter((task) => task.status === "approved").length;

  return (
    <section className="page-section" aria-labelledby="queue-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">审批与执行</p>
          <h1 id="queue-title">入库队列</h1>
        </div>
        <StatusBadge status={queueStatus(tasks, error)} />
      </div>

      {(error || notice) && <small role="status">{error || notice}</small>}

      <div className="work-panel">
        <h2>待处理任务</h2>
        {approvedCount > 0 && <small role="status">已通过待执行：{approvedCount} 条</small>}
        <div className="task-list">
          {manualTasks.length === 0 ? (
            <div className="empty-state">{loading ? "正在加载入库任务" : "暂无待人工处理任务"}</div>
          ) : (
            manualTasks.map((task) => {
              const isExpanded = expandedTaskIds.has(task.id);
              const metadataText = task.metadata ? JSON.stringify(task.metadata, null, 2) : "";
              return (
                <div className="task-row" key={task.id}>
                  <div className="task-summary">
                    <div className="task-main">
                      <span className={`status-dot status-${task.status}`} />
                      <div>
                        <strong>{task.title ?? task.path ?? `任务 #${task.id}`}</strong>
                        <small>
                          #{task.id} · {task.source_id ?? "未知来源"} · {task.path ?? "未生成路径"}
                        </small>
                        {task.reason && <small>原因：{task.reason}</small>}
                      </div>
                    </div>
                    <div className="task-actions">
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`${isExpanded ? "收起" : "查看"}任务 ${task.id} 详情`}
                        aria-expanded={isExpanded}
                        onClick={() => toggleDetails(task.id)}
                      >
                        {isExpanded ? (
                          <ChevronDown aria-hidden="true" size={16} />
                        ) : (
                          <ChevronRight aria-hidden="true" size={16} />
                        )}
                        详情
                      </button>
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`通过任务 ${task.id}`}
                        onClick={() => handleApprove(task)}
                        disabled={activeTaskId === task.id || task.status !== "pending"}
                      >
                        <Check aria-hidden="true" size={16} />
                        通过
                      </button>
                      <button
                        className="icon-button"
                        type="button"
                        aria-label={`将任务 ${task.id} 的网站设为信源`}
                        onClick={() => openTrustPanel(task.id)}
                        disabled={activeTaskId === task.id || task.status !== "pending"}
                      >
                        <ShieldCheck aria-hidden="true" size={16} />
                        信源
                      </button>
                      <button
                        className="icon-button danger"
                        type="button"
                        aria-label={`拒绝任务 ${task.id}`}
                        onClick={() => handleReject(task)}
                        disabled={activeTaskId === task.id || task.status !== "pending"}
                      >
                        <X aria-hidden="true" size={16} />
                        拒绝
                      </button>
                    </div>
                  </div>
                  {trustTaskId === task.id && (
                    <div className="trust-source-panel">
                      <div className="segmented-control" aria-label="信源入库方式">
                        <label>
                          <input
                            type="radio"
                            name={`trust-mode-${task.id}`}
                            checked={trustMode === "manual"}
                            onChange={() => setTrustMode("manual")}
                          />
                          按需
                        </label>
                        <label>
                          <input
                            type="radio"
                            name={`trust-mode-${task.id}`}
                            checked={trustMode === "scheduled"}
                            onChange={() => setTrustMode("scheduled")}
                          />
                          定期
                        </label>
                      </div>
                      {trustMode === "scheduled" && (
                        <label className="field-row">
                          <span>频率</span>
                          <select
                            aria-label="频率"
                            value={trustFrequency}
                            onChange={(event) => setTrustFrequency(event.target.value as "daily" | "weekly" | "monthly")}
                          >
                            <option value="daily">每天</option>
                            <option value="weekly">每周</option>
                            <option value="monthly">每月</option>
                          </select>
                        </label>
                      )}
                      <button
                        className="icon-button"
                        type="button"
                        onClick={() => handleTrustSource(task)}
                        disabled={activeTaskId === task.id}
                      >
                        <ShieldCheck aria-hidden="true" size={16} />
                        确认设为信源
                      </button>
                    </div>
                  )}
                  {isExpanded && (
                    <div className="task-details">
                      <dl>
                        <div>
                          <dt>链接</dt>
                          <dd>
                            {task.canonical_url ? (
                              <a href={task.canonical_url} target="_blank" rel="noreferrer">
                                {task.canonical_url}
                              </a>
                            ) : (
                              "未记录"
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt>Raw 路径</dt>
                          <dd>{task.raw_path ?? task.path ?? "未生成路径"}</dd>
                        </div>
                        <div>
                          <dt>大小</dt>
                          <dd>{task.content_bytes === undefined ? "未知" : `${task.content_bytes} bytes`}</dd>
                        </div>
                        <div>
                          <dt>Domain</dt>
                          <dd>{task.target_domain ?? "未知"}</dd>
                        </div>
                      </dl>
                      {metadataText && (
                        <div>
                          <h3>Metadata</h3>
                          <pre>{metadataText}</pre>
                        </div>
                      )}
                      {task.content_preview && (
                        <div>
                          <h3>内容预览</h3>
                          <pre>{task.content_preview}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}
