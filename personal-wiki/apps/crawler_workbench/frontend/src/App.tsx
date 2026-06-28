import { BookOpen, DatabaseZap, Gauge, ListChecks, Microchip, Rss, Settings, Waypoints } from "lucide-react";
import { useMemo, useState } from "react";

import { Layout, type NavigationItem } from "./components/Layout";
import { AcceleratorSpecsPage } from "./pages/AcceleratorSpecsPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { OverviewPage } from "./pages/OverviewPage";
import { QueuePage } from "./pages/QueuePage";
import { SettingsPage } from "./pages/SettingsPage";
import { SourcesPage } from "./pages/SourcesPage";
import { SourceWorkbenchPage } from "./pages/SourceWorkbenchPage";
import type { PageKey } from "./types";

const warningText = "无登录：仅可暴露在可信网络。后端可触发本机 Codex。";

function App() {
  const [activePage, setActivePage] = useState<PageKey>("overview");

  const navigation = useMemo<NavigationItem[]>(
    () => [
      { key: "overview", label: "运维控制台", icon: Gauge },
      { key: "sources", label: "来源订阅", icon: Rss },
      { key: "queue", label: "入库队列", icon: ListChecks },
      { key: "knowledge", label: "知识工作台", icon: BookOpen },
      { key: "acceleratorSpecs", label: "参数库", icon: Microchip },
      { key: "sourceWorkbench", label: "来源工作台", icon: DatabaseZap },
      { key: "settings", label: "设置", icon: Settings }
    ],
    []
  );

  return (
    <Layout activePage={activePage} navigation={navigation} onNavigate={setActivePage}>
      <div className="warning" role="status">
        {warningText}
      </div>
      {activePage === "overview" && <OverviewPage />}
      {activePage === "sources" && <SourcesPage />}
      {activePage === "queue" && <QueuePage />}
      {activePage === "knowledge" && <KnowledgePage />}
      {activePage === "acceleratorSpecs" && <AcceleratorSpecsPage />}
      {activePage === "sourceWorkbench" && <SourceWorkbenchPage />}
      {activePage === "settings" && <SettingsPage />}
      <div className="footer-note">
        <Waypoints aria-hidden="true" size={15} />
        本地工作台连接 Personal Wiki 数据、队列与 Codex 执行状态。
      </div>
    </Layout>
  );
}

export default App;
