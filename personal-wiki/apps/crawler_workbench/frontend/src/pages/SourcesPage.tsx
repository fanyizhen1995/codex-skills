import { Play } from "lucide-react";

import { StatusBadge } from "../components/StatusBadge";
import type { SourceProfile } from "../types";

const sources: SourceProfile[] = [
  {
    id: "rss-engineering",
    name: "Engineering RSS",
    type: "rss",
    target_domain: "engineering",
    url: "https://example.com/feed.xml",
    trust_level: "trusted",
    schedule: "daily 09:30",
    auto_ingest: true,
    auth_required: false,
    auth_state: "ready",
    topic: "platform",
    enabled: true,
    last_run_at: "2026-06-25 09:31",
    last_run_status: "succeeded"
  },
  {
    id: "github-watch",
    name: "GitHub Watch",
    type: "github",
    target_domain: "engineering",
    url: "https://github.com/org/repo",
    trust_level: "trusted",
    schedule: "hourly",
    auto_ingest: false,
    auth_required: true,
    auth_state: "ready",
    topic: "code",
    enabled: true,
    last_run_at: "2026-06-25 10:15",
    last_run_status: "succeeded"
  },
  {
    id: "arxiv-ai",
    name: "Arxiv AI",
    type: "arxiv",
    target_domain: "research",
    url: "https://arxiv.org/list/cs.AI/recent",
    trust_level: "review",
    schedule: "weekday 14:00",
    auto_ingest: false,
    auth_required: false,
    auth_state: "ready",
    topic: "ai",
    enabled: true,
    last_run_at: "2026-06-24 14:02",
    last_run_status: "succeeded"
  },
  {
    id: "web-news",
    name: "News Site",
    type: "web",
    target_domain: "market",
    url: "https://news.example.com",
    trust_level: "review",
    schedule: "daily 16:00",
    auto_ingest: false,
    auth_required: true,
    auth_state: "needs_auth_config",
    topic: "market",
    enabled: true,
    last_run_at: "2026-06-24 16:03",
    last_run_status: "failed"
  }
];

function groupKey(source: SourceProfile) {
  return `${source.type} / ${source.target_domain}`;
}

const groupedSources = sources.reduce<Record<string, SourceProfile[]>>((groups, source) => {
  const key = groupKey(source);
  groups[key] = [...(groups[key] ?? []), source];
  return groups;
}, {});

export function SourcesPage() {
  return (
    <section className="page-section" aria-labelledby="sources-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">订阅与抓取</p>
          <h1 id="sources-title">来源订阅</h1>
        </div>
        <StatusBadge status="trusted" />
      </div>

      <div className="source-groups">
        {Object.entries(groupedSources).map(([group, items]) => (
          <div className="work-panel" key={group}>
            <h2>{group}</h2>
            <div className="responsive-table" role="table" aria-label={`${group} 来源`}>
              <div className="table-row table-head" role="row">
                <span role="columnheader">来源</span>
                <span role="columnheader">信任</span>
                <span role="columnheader">计划</span>
                <span role="columnheader">认证</span>
                <span role="columnheader">上次运行</span>
                <span role="columnheader">操作</span>
              </div>
              {items.map((source) => (
                <div className="table-row" role="row" key={source.id}>
                  <span role="cell">
                    <strong>{source.name}</strong>
                    <small>{source.url}</small>
                  </span>
                  <span role="cell">{source.trust_level}</span>
                  <span role="cell">{source.schedule}</span>
                  <span role="cell">{source.auth_state}</span>
                  <span role="cell">
                    {source.last_run_at}
                    <small>{source.last_run_status}</small>
                  </span>
                  <span role="cell">
                    <button className="icon-button" type="button" aria-label={`运行 ${source.name}`}>
                      <Play aria-hidden="true" size={16} />
                      运行
                    </button>
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
