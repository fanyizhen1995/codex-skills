import { StatusBadge } from "../components/StatusBadge";

export function OverviewPage() {
  return (
    <section className="page-section" aria-labelledby="overview-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">运行状态</p>
          <h1 id="overview-title">控制台概览</h1>
        </div>
        <StatusBadge status="ready" />
      </div>
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">来源同步</span>
          <strong>待连接</strong>
          <span className="metric-help">读取 /api/sources 与 /api/runs</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">入库队列</span>
          <strong>待连接</strong>
          <span className="metric-help">审批、拒绝、执行待入库任务</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">知识索引</span>
          <strong>待连接</strong>
          <span className="metric-help">搜索、问答、图谱与校验</span>
        </div>
      </div>
    </section>
  );
}
