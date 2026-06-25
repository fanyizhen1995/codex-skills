import { Check, X } from "lucide-react";
import { useEffect, useState } from "react";

import { approveTask, getQueue, rejectTask } from "../api";
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

export function QueuePage() {
  const [tasks, setTasks] = useState<IngestTask[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);

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
        <div className="task-list">
          {tasks.length === 0 ? (
            <div className="empty-state">{loading ? "正在加载入库任务" : "暂无入库任务"}</div>
          ) : (
            tasks.map((task) => (
              <div className="task-row" key={task.id}>
                <div className="task-main">
                  <span className={`status-dot status-${task.status}`} />
                  <div>
                    <strong>{task.title ?? task.path ?? `任务 #${task.id}`}</strong>
                    <small>
                      #{task.id} · {task.source_id ?? "未知来源"} · {task.path ?? "未生成路径"}
                    </small>
                    {task.reason && <small>失败原因：{task.reason}</small>}
                  </div>
                </div>
                <div className="task-actions">
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
            ))
          )}
        </div>
      </div>
    </section>
  );
}
