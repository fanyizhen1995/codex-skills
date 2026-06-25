import { StatusBadge } from "../components/StatusBadge";

export function KnowledgePage() {
  return (
    <section className="page-section" aria-labelledby="knowledge-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">检索与问答</p>
          <h1 id="knowledge-title">知识工作台</h1>
        </div>
        <StatusBadge status="trusted" />
      </div>
      <div className="work-panel">
        <h2>知识查询</h2>
        <p>面向 /api/search、/api/ask、/api/graph 和 /api/validate 的操作区域。</p>
      </div>
    </section>
  );
}
