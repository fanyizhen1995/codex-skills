import { Check, X } from "lucide-react";

import { StatusBadge } from "../components/StatusBadge";
import type { IngestTask } from "../types";

const tasks: IngestTask[] = [
  {
    id: 101,
    source_id: "rss-engineering",
    target_domain: "engineering",
    status: "pending",
    title: "Runtime incident notes",
    path: "engineering/runtime/incident-notes.md",
    created_at: "2026-06-25 09:42"
  },
  {
    id: 102,
    source_id: "github-watch",
    target_domain: "engineering",
    status: "running",
    title: "Release checklist update",
    path: "engineering/release/checklist.md",
    created_at: "2026-06-25 10:18"
  },
  {
    id: 103,
    source_id: "web-news",
    target_domain: "market",
    status: "failed",
    title: "Market brief",
    path: "market/briefs/today.md",
    reason: "正文抽取为空",
    created_at: "2026-06-24 16:12"
  }
];

export function QueuePage() {
  return (
    <section className="page-section" aria-labelledby="queue-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">审批与执行</p>
          <h1 id="queue-title">入库队列</h1>
        </div>
        <StatusBadge status="running" />
      </div>

      <div className="work-panel">
        <h2>待处理任务</h2>
        <div className="task-list">
          {tasks.map((task) => (
            <div className="task-row" key={task.id}>
              <div className="task-main">
                <span className={`status-dot status-${task.status}`} />
                <div>
                  <strong>{task.title}</strong>
                  <small>
                    #{task.id} · {task.source_id} · {task.path}
                  </small>
                  {task.reason && <small>失败原因：{task.reason}</small>}
                </div>
              </div>
              <div className="task-actions">
                <button className="icon-button" type="button" aria-label={`通过任务 ${task.id}`}>
                  <Check aria-hidden="true" size={16} />
                  通过
                </button>
                <button className="icon-button danger" type="button" aria-label={`拒绝任务 ${task.id}`}>
                  <X aria-hidden="true" size={16} />
                  拒绝
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
