import { AlertTriangle, CalendarClock, GitCommit, ShieldAlert } from "lucide-react";

import { TrendChart, type TrendPoint } from "../components/TrendChart";
import { StatusBadge } from "../components/StatusBadge";

const trendData: TrendPoint[] = [
  { label: "周一", fetched: 18, changed: 7, failed: 1 },
  { label: "周二", fetched: 24, changed: 10, failed: 2 },
  { label: "周三", fetched: 21, changed: 8, failed: 0 },
  { label: "周四", fetched: 31, changed: 13, failed: 3 },
  { label: "周五", fetched: 27, changed: 11, failed: 1 }
];

const scheduledRuns = [
  { source: "Engineering RSS", time: "09:30", scope: "daily" },
  { source: "GitHub Watch", time: "10:15", scope: "hourly" },
  { source: "Arxiv AI", time: "14:00", scope: "weekday" }
];

const authWarnings = ["GitHub token 将在 3 天后过期", "网页来源 news-site 需要 cookie 刷新"];
const validationFailures = ["docs/ai/index.md 缺少 frontmatter", "crawler/reports/june.md 链接校验失败"];
const recentCommits = ["source:github 同步 8 篇变更", "source:rss 入库 5 篇摘要", "queue:auto 修复 2 个标题"];
const failureReasons = ["认证失败 5", "正文为空 3", "超时 2"];

export function OverviewPage() {
  return (
    <section className="page-section" aria-labelledby="overview-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">运行状态</p>
          <h1 id="overview-title">运维控制台</h1>
        </div>
        <StatusBadge status="ready" />
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">运行健康</span>
          <strong>稳定</strong>
          <span className="metric-help">API 在线，最近 24 小时失败率 4%</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">待处理入库</span>
          <strong>12</strong>
          <span className="metric-help">8 个待审批，3 个运行中，1 个失败</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">来源覆盖</span>
          <strong>4 类</strong>
          <span className="metric-help">RSS、GitHub、Arxiv、Web 均已启用</span>
        </div>
      </div>

      <div className="panel-grid">
        <div className="work-panel">
          <h2>
            <CalendarClock aria-hidden="true" size={17} />
            下一批计划抓取
          </h2>
          <div className="compact-list">
            {scheduledRuns.map((run) => (
              <div className="list-row" key={run.source}>
                <span>{run.source}</span>
                <strong>{run.time}</strong>
                <span>{run.scope}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="work-panel">
          <h2>
            <ShieldAlert aria-hidden="true" size={17} />
            认证告警
          </h2>
          <ul className="plain-list">
            {authWarnings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="work-panel">
          <h2>
            <AlertTriangle aria-hidden="true" size={17} />
            校验失败
          </h2>
          <ul className="plain-list">
            {validationFailures.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="work-panel">
          <h2>
            <GitCommit aria-hidden="true" size={17} />
            最近自动提交
          </h2>
          <ul className="plain-list">
            {recentCommits.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="work-panel">
          <h2>失败原因分布</h2>
          <ul className="plain-list">
            {failureReasons.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="work-panel chart-panel">
        <h2>抓取趋势</h2>
        <TrendChart data={trendData} />
      </div>
    </section>
  );
}
