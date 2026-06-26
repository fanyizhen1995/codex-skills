import { StatusBadge } from "../components/StatusBadge";

export function SettingsPage() {
  return (
    <section className="page-section" aria-labelledby="settings-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">本机配置</p>
          <h1 id="settings-title">设置</h1>
        </div>
        <StatusBadge status="untrusted" />
      </div>
      <div className="work-panel">
        <h2>运行参数</h2>
        <p>显示绑定地址、端口、Wiki 根目录、数据库位置与可信网络提示。</p>
      </div>
    </section>
  );
}
