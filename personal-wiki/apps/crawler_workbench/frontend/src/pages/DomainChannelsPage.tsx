import { KeyRound, Plus, RefreshCw, Save, ShieldCheck, Wifi } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createChannel,
  createSource,
  getChannelProbeRuns,
  getChannels,
  getDomains,
  getSourcesForChannel,
  probeChannel,
  setChannelSecret,
  updateChannel
} from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { Channel, ChannelPayload, ChannelProbeRun, Domain, SourcePayload, SourceProfile, Status } from "../types";

const defaultDomain = "ai_infra";

const initialChannelForm: ChannelPayload = {
  target_domain: defaultDomain,
  name: "",
  base_url: "",
  probe_url: "",
  kind: "web",
  connector: "generic",
  trust_level: "trusted",
  enabled: true,
  auth_required: false,
  auth_mode: "none",
  notes: ""
};

const initialSourceForm = {
  id: "",
  name: "",
  url: "",
  fetcher_type: "web_page",
  topic: "",
  schedule: "weekly",
  type: "web"
};

function statusForChannel(channel?: Channel | null): Status {
  if (!channel) {
    return "pending";
  }
  if (!channel.enabled) {
    return "failed";
  }
  if (channel.auth_state === "ready") {
    return "ready";
  }
  if (
    channel.auth_state === "needs_auth_config" ||
    channel.auth_state === "auth_failed" ||
    channel.auth_state === "needs_browser" ||
    channel.auth_state === "network_failed" ||
    channel.auth_state === "unsupported"
  ) {
    return channel.auth_state;
  }
  return "pending";
}

function timeLabel(value?: string | null) {
  if (!value) {
    return "未验证";
  }
  const parsed = new Date(value.includes("T") ? value : value.replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function sourceTypeFor(fetcherType: string) {
  if (fetcherType.startsWith("github_")) {
    return "github";
  }
  if (fetcherType === "rss_feed") {
    return "rss";
  }
  if (fetcherType === "arxiv_query") {
    return "arxiv";
  }
  return "web";
}

export function DomainChannelsPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [selectedDomain, setSelectedDomain] = useState(defaultDomain);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [sources, setSources] = useState<SourceProfile[]>([]);
  const [probeRuns, setProbeRuns] = useState<ChannelProbeRun[]>([]);
  const [search, setSearch] = useState("");
  const [channelForm, setChannelForm] = useState<ChannelPayload>(initialChannelForm);
  const [selectedNotes, setSelectedNotes] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [sourceForm, setSourceForm] = useState(initialSourceForm);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  async function loadChannels(domain = selectedDomain) {
    setLoading(true);
    try {
      const [domainPayload, channelPayload] = await Promise.all([getDomains(), getChannels(domain)]);
      setDomains(domainPayload);
      setChannels(channelPayload);
      setError("");
      const nextSelected = channelPayload.some((channel) => channel.id === selectedChannelId)
        ? selectedChannelId
        : channelPayload[0]?.id ?? "";
      setSelectedChannelId(nextSelected);
      return { channels: channelPayload, selectedId: nextSelected };
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载渠道失败");
      return { channels: [], selectedId: "" };
    } finally {
      setLoading(false);
    }
  }

  async function loadSelectedDetails(channelId: string, domain = selectedDomain) {
    if (!channelId) {
      setSources([]);
      setProbeRuns([]);
      return;
    }
    try {
      const [sourcePayload, probePayload] = await Promise.all([
        getSourcesForChannel(domain, channelId),
        getChannelProbeRuns(channelId)
      ]);
      setSources(sourcePayload);
      setProbeRuns(probePayload);
      setError("");
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载渠道详情失败");
    }
  }

  useEffect(() => {
    loadChannels(selectedDomain);
  }, [selectedDomain]);

  useEffect(() => {
    loadSelectedDetails(selectedChannelId, selectedDomain);
  }, [selectedChannelId, selectedDomain]);

  useEffect(() => {
    const channel = channels.find((item) => item.id === selectedChannelId);
    setSelectedNotes(channel?.notes ?? "");
  }, [selectedChannelId, channels]);

  useEffect(() => {
    setChannelForm((current) => ({ ...current, target_domain: selectedDomain }));
  }, [selectedDomain]);

  const selectedChannel = channels.find((channel) => channel.id === selectedChannelId) ?? null;
  const filteredChannels = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return channels;
    }
    return channels.filter((channel) =>
      [channel.name, channel.base_url, channel.connector, channel.kind, channel.auth_state]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [channels, search]);

  async function refreshAll() {
    const result = await loadChannels(selectedDomain);
    await loadSelectedDetails(result.selectedId, selectedDomain);
  }

  async function handleCreateChannel(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: ChannelPayload = {
      ...channelForm,
      name: channelForm.name.trim(),
      base_url: channelForm.base_url.trim(),
      probe_url: channelForm.probe_url?.trim() ?? "",
      connector: channelForm.connector.trim() || "generic",
      notes: channelForm.notes.trim()
    };
    if (!payload.name || !payload.base_url) {
      setError("Channel name 和 Base URL 必填");
      return;
    }
    setBusy("create-channel");
    setNotice("");
    setError("");
    try {
      const created = await createChannel(payload);
      const result = await loadChannels(selectedDomain);
      setSelectedChannelId(created.id || result.selectedId);
      setChannelForm({ ...initialChannelForm, target_domain: selectedDomain });
      setNotice(`${created.name} 已创建`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "创建渠道失败");
    } finally {
      setBusy("");
    }
  }

  async function handleSaveSelected() {
    if (!selectedChannel) {
      return;
    }
    setBusy("save-channel");
    setNotice("");
    setError("");
    try {
      const updated = await updateChannel(selectedChannel.id, { notes: selectedNotes });
      setChannels((current) => current.map((channel) => (channel.id === updated.id ? updated : channel)));
      setNotice(`${updated.name} 已保存`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "保存渠道失败");
    } finally {
      setBusy("");
    }
  }

  async function handleReplaceSecret(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedChannel || !secretValue.trim()) {
      return;
    }
    setBusy("secret");
    setNotice("");
    setError("");
    try {
      const response = await setChannelSecret(selectedChannel.id, {
        secret_kind: "synthetic_token",
        secret: secretValue
      });
      setSecretValue("");
      setChannels((current) =>
        current.map((channel) =>
          channel.id === selectedChannel.id
            ? { ...channel, secret_configured: response.secret_configured, auth_state: response.auth_state }
            : channel
        )
      );
      setNotice("Secret 已替换");
    } catch (error) {
      setError(error instanceof Error ? error.message : "替换 secret 失败");
    } finally {
      setBusy("");
    }
  }

  async function handleProbe() {
    if (!selectedChannel) {
      return;
    }
    setBusy("probe");
    setNotice("");
    setError("");
    try {
      const run = await probeChannel(selectedChannel.id);
      const runs = await getChannelProbeRuns(selectedChannel.id);
      setProbeRuns(runs.length ? runs : [run, ...probeRuns]);
      setChannels((current) =>
        current.map((channel) =>
          channel.id === selectedChannel.id
            ? {
                ...channel,
                auth_state: run.status,
                last_probe_status: run.status,
                last_probe_at: run.finished_at ?? run.started_at,
                last_probe_summary: run.summary
              }
            : channel
        )
      );
      setNotice(`Verify Access：${run.status}`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "验证访问失败");
    } finally {
      setBusy("");
    }
  }

  async function handleCreateSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedChannel) {
      return;
    }
    const payload: SourcePayload = {
      id: sourceForm.id.trim(),
      name: sourceForm.name.trim(),
      type: sourceForm.type || sourceTypeFor(sourceForm.fetcher_type),
      fetcher_type: sourceForm.fetcher_type,
      target_domain: selectedDomain,
      url: sourceForm.url.trim(),
      channel_id: selectedChannel.id,
      trust_level: "trusted",
      schedule: sourceForm.schedule,
      run_policy: "scheduled",
      auto_ingest: true,
      auth_required: false,
      topic: sourceForm.topic.trim(),
      enabled: true
    };
    if (!payload.id || !payload.name || !payload.url || !payload.topic) {
      setError("Source id、name、URL 和 topic 必填");
      return;
    }
    setBusy("source");
    setNotice("");
    setError("");
    try {
      const created = await createSource(payload);
      setSources((current) => [...current.filter((source) => source.id !== created.id), created]);
      setSourceForm(initialSourceForm);
      setNotice(`${created.name} 已添加`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "添加 source 失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="page-section domain-channel-page" aria-labelledby="domain-channels-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">访问边界与具体来源</p>
          <h1 id="domain-channels-title">Domain Channels</h1>
        </div>
        <div className="inline-actions">
          <button className="icon-button" type="button" onClick={refreshAll} disabled={loading}>
            <RefreshCw aria-hidden="true" size={16} />
            Refresh
          </button>
          <StatusBadge status={statusForChannel(selectedChannel)} />
        </div>
      </div>

      {(error || notice) && <small role="status">{error || notice}</small>}

      <div className="domain-channel-grid">
        <aside className="work-panel channel-rail" aria-label="Channel filters">
          <label className="stacked-field">
            <span>Domain</span>
            <select value={selectedDomain} onChange={(event) => setSelectedDomain(event.target.value)}>
              {(domains.length ? domains : [{ id: defaultDomain, name: defaultDomain }]).map((domain) => (
                <option key={domain.id} value={domain.id}>
                  {domain.name}
                </option>
              ))}
            </select>
          </label>
          <label className="stacked-field">
            <span>Search</span>
            <input
              aria-label="Search channels"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="github, api, arxiv"
            />
          </label>
          <form className="channel-create-form" onSubmit={handleCreateChannel}>
            <h2>
              <Plus aria-hidden="true" size={16} />
              New channel
            </h2>
            <label className="stacked-field">
              <span>Channel name</span>
              <input
                aria-label="Channel name"
                value={channelForm.name}
                onChange={(event) => setChannelForm((current) => ({ ...current, name: event.target.value }))}
              />
            </label>
            <label className="stacked-field">
              <span>Base URL</span>
              <input
                aria-label="Base URL"
                value={channelForm.base_url}
                onChange={(event) => setChannelForm((current) => ({ ...current, base_url: event.target.value }))}
                placeholder="https://github.com"
              />
            </label>
            <label className="stacked-field">
              <span>Probe URL</span>
              <input
                aria-label="Probe URL"
                value={channelForm.probe_url}
                onChange={(event) => setChannelForm((current) => ({ ...current, probe_url: event.target.value }))}
                placeholder="https://api.github.com/user"
              />
            </label>
            <div className="field-pair">
              <label className="stacked-field">
                <span>Kind</span>
                <select
                  aria-label="Kind"
                  value={channelForm.kind}
                  onChange={(event) => setChannelForm((current) => ({ ...current, kind: event.target.value }))}
                >
                  <option value="web">web</option>
                  <option value="api">api</option>
                  <option value="browser">browser</option>
                  <option value="mcp">mcp</option>
                  <option value="command">command</option>
                </select>
              </label>
              <label className="stacked-field">
                <span>Connector</span>
                <select
                  aria-label="Connector"
                  value={channelForm.connector}
                  onChange={(event) => setChannelForm((current) => ({ ...current, connector: event.target.value }))}
                >
                  <option value="generic">generic</option>
                  <option value="github">github</option>
                  <option value="arxiv">arxiv</option>
                  <option value="rss">rss</option>
                </select>
              </label>
            </div>
            <div className="field-pair">
              <label className="stacked-field">
                <span>Auth mode</span>
                <select
                  aria-label="Auth mode"
                  value={channelForm.auth_mode}
                  onChange={(event) => setChannelForm((current) => ({ ...current, auth_mode: event.target.value }))}
                >
                  <option value="none">none</option>
                  <option value="token">token</option>
                  <option value="cookie">cookie</option>
                  <option value="header">header</option>
                  <option value="basic">basic</option>
                  <option value="oauth_placeholder">oauth_placeholder</option>
                </select>
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={channelForm.auth_required}
                  onChange={(event) =>
                    setChannelForm((current) => ({
                      ...current,
                      auth_required: event.target.checked,
                      auth_mode: event.target.checked && current.auth_mode === "none" ? "token" : current.auth_mode
                    }))
                  }
                />
                Auth required
              </label>
            </div>
            <label className="stacked-field">
              <span>Channel notes</span>
              <textarea
                aria-label="Channel notes"
                value={channelForm.notes}
                onChange={(event) => setChannelForm((current) => ({ ...current, notes: event.target.value }))}
                rows={3}
              />
            </label>
            <button className="icon-button" type="submit" disabled={busy === "create-channel"}>
              <Plus aria-hidden="true" size={16} />
              Add channel
            </button>
          </form>
        </aside>

        <div className="work-panel channel-table-panel">
          <h2>Channels</h2>
          <div className="responsive-table channel-table" role="table" aria-label="Domain channels">
            <div className="table-row table-head channel-row" role="row">
              <span role="columnheader">Name</span>
              <span role="columnheader">Base URL</span>
              <span role="columnheader">Access</span>
              <span role="columnheader">Sources</span>
            </div>
            {filteredChannels.length === 0 ? (
              <div className="empty-state">{loading ? "正在加载渠道" : "暂无渠道"}</div>
            ) : (
              filteredChannels.map((channel) => (
                <button
                  className={`table-row channel-row channel-select-row${
                    channel.id === selectedChannelId ? " active" : ""
                  }`}
                  key={channel.id}
                  type="button"
                  role="row"
                  aria-label={`Select channel ${channel.name}`}
                  onClick={() => setSelectedChannelId(channel.id)}
                >
                  <span role="cell">
                    <strong>{channel.name}</strong>
                    <small>
                      {channel.kind} · {channel.connector}
                    </small>
                  </span>
                  <span role="cell">{channel.base_url}</span>
                  <span role="cell">
                    <StatusBadge status={statusForChannel(channel)} />
                    <small>{channel.last_probe_summary ?? "未验证"}</small>
                  </span>
                  <span role="cell">{channel.source_count} sources</span>
                </button>
              ))
            )}
          </div>
        </div>

        <aside className="work-panel channel-detail-panel" aria-label="Channel details">
          {selectedChannel ? (
            <>
              <div className="detail-title">
                <div>
                  <h2>{selectedChannel.name}</h2>
                  <small>{selectedChannel.base_url}</small>
                </div>
                <StatusBadge status={statusForChannel(selectedChannel)} />
              </div>

              <dl className="channel-facts">
                <div>
                  <dt>Auth</dt>
                  <dd>
                    {selectedChannel.auth_mode} · {selectedChannel.secret_configured ? "secret configured" : "no secret"}
                  </dd>
                </div>
                <div>
                  <dt>Last probe</dt>
                  <dd>{timeLabel(selectedChannel.last_probe_at)}</dd>
                </div>
                <div>
                  <dt>Sources</dt>
                  <dd>{sources.length}</dd>
                </div>
              </dl>

              <label className="stacked-field">
                <span>Selected notes</span>
                <textarea
                  aria-label="Selected notes"
                  value={selectedNotes}
                  onChange={(event) => setSelectedNotes(event.target.value)}
                  rows={3}
                />
              </label>
              <button className="icon-button" type="button" onClick={handleSaveSelected} disabled={busy === "save-channel"}>
                <Save aria-hidden="true" size={16} />
                Save channel
              </button>

              <form className="secret-form" onSubmit={handleReplaceSecret}>
                <h2>
                  <KeyRound aria-hidden="true" size={16} />
                  Secret
                </h2>
                <label className="stacked-field">
                  <span>Secret value</span>
                  <input
                    aria-label="Secret value"
                    type="password"
                    value={secretValue}
                    onChange={(event) => setSecretValue(event.target.value)}
                    placeholder="synthetic token or cookie"
                  />
                </label>
                <button className="icon-button" type="submit" disabled={busy === "secret" || !secretValue.trim()}>
                  <ShieldCheck aria-hidden="true" size={16} />
                  Replace secret
                </button>
              </form>

              <div className="probe-panel">
                <div className="detail-title">
                  <h2>Probe history</h2>
                  <button className="icon-button" type="button" onClick={handleProbe} disabled={busy === "probe"}>
                    <Wifi aria-hidden="true" size={16} />
                    Verify access
                  </button>
                </div>
                <div className="probe-list">
                  {probeRuns.length === 0 ? (
                    <div className="empty-state">暂无 probe history</div>
                  ) : (
                    probeRuns.map((run) => (
                      <div className="info-row" key={run.id}>
                        <div className="info-main">
                          <strong>Probe #{run.id}</strong>
                          <span>{run.summary}</span>
                          <small>
                            {run.status} · {run.http_status ?? "n/a"} · {timeLabel(run.finished_at ?? run.started_at)}
                          </small>
                        </div>
                        <StatusBadge status={statusForChannel({ ...selectedChannel, auth_state: run.status })} />
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="child-source-panel">
                <h2>Child sources</h2>
                <div className="info-list">
                  {sources.length === 0 ? (
                    <div className="empty-state">暂无 child source</div>
                  ) : (
                    sources.map((source) => (
                      <div className="info-row" key={source.id}>
                        <div className="info-main">
                          <strong>{source.name}</strong>
                          <span>{source.url}</span>
                          <small>
                            {source.fetcher_type ?? source.type} · {source.schedule}
                          </small>
                        </div>
                        <StatusBadge status={source.enabled ? "ready" : "failed"} />
                      </div>
                    ))
                  )}
                </div>
                <form className="source-create-form" onSubmit={handleCreateSource}>
                  <label className="stacked-field">
                    <span>Source id</span>
                    <input
                      aria-label="Source id"
                      value={sourceForm.id}
                      onChange={(event) => setSourceForm((current) => ({ ...current, id: event.target.value }))}
                    />
                  </label>
                  <label className="stacked-field">
                    <span>Source name</span>
                    <input
                      aria-label="Source name"
                      value={sourceForm.name}
                      onChange={(event) => setSourceForm((current) => ({ ...current, name: event.target.value }))}
                    />
                  </label>
                  <label className="stacked-field">
                    <span>Source URL</span>
                    <input
                      aria-label="Source URL"
                      value={sourceForm.url}
                      onChange={(event) => setSourceForm((current) => ({ ...current, url: event.target.value }))}
                    />
                  </label>
                  <div className="field-pair">
                    <label className="stacked-field">
                      <span>Fetcher type</span>
                      <select
                        aria-label="Fetcher type"
                        value={sourceForm.fetcher_type}
                        onChange={(event) =>
                          setSourceForm((current) => ({
                            ...current,
                            fetcher_type: event.target.value,
                            type: sourceTypeFor(event.target.value)
                          }))
                        }
                      >
                        <option value="web_page">web_page</option>
                        <option value="rss_feed">rss_feed</option>
                        <option value="github_repo">github_repo</option>
                        <option value="github_issues">github_issues</option>
                        <option value="github_releases">github_releases</option>
                        <option value="arxiv_query">arxiv_query</option>
                        <option value="api_endpoint">api_endpoint</option>
                        <option value="browser_flow">browser_flow</option>
                      </select>
                    </label>
                    <label className="stacked-field">
                      <span>Schedule</span>
                      <select
                        aria-label="Schedule"
                        value={sourceForm.schedule}
                        onChange={(event) => setSourceForm((current) => ({ ...current, schedule: event.target.value }))}
                      >
                        <option value="manual">manual</option>
                        <option value="daily">daily</option>
                        <option value="weekly">weekly</option>
                        <option value="monthly">monthly</option>
                      </select>
                    </label>
                  </div>
                  <label className="stacked-field">
                    <span>Topic</span>
                    <input
                      aria-label="Topic"
                      value={sourceForm.topic}
                      onChange={(event) => setSourceForm((current) => ({ ...current, topic: event.target.value }))}
                    />
                  </label>
                  <button className="icon-button" type="submit" disabled={busy === "source"}>
                    <Plus aria-hidden="true" size={16} />
                    Add child source
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="empty-state">选择一个 channel 查看详情</div>
          )}
        </aside>
      </div>
    </section>
  );
}
