import { StatusBadge } from "../components/StatusBadge";

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
        <p>用于查看候选内容，执行 approve、reject、run 和 commit 操作。</p>
      </div>
    </section>
  );
}
