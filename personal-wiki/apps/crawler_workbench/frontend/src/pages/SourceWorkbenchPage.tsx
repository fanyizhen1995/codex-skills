import { StatusBadge } from "../components/StatusBadge";

export function SourceWorkbenchPage() {
  return (
    <section className="page-section" aria-labelledby="source-workbench-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">来源诊断</p>
          <h1 id="source-workbench-title">来源工作台</h1>
        </div>
        <StatusBadge status="needs_auth_config" />
      </div>
      <div className="work-panel">
        <h2>抓取诊断</h2>
        <p>用于排查认证状态、抓取结果、原始内容和入库前转换记录。</p>
      </div>
    </section>
  );
}
