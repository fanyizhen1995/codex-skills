import { StatusBadge } from "../components/StatusBadge";

export function SourceSubscriptionsPage() {
  return (
    <section className="page-section" aria-labelledby="sources-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">订阅与抓取</p>
          <h1 id="sources-title">来源订阅</h1>
        </div>
        <StatusBadge status="pending" />
      </div>
      <div className="work-panel">
        <h2>来源清单</h2>
        <p>这里承载 RSS、GitHub、Arxiv 与网页来源的启停、信任级别和手动抓取入口。</p>
      </div>
    </section>
  );
}
