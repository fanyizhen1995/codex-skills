import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { getDomains, getWikiPage, getWikiPages } from "../api";
import type { Domain, WikiPageDetail, WikiPageSummary } from "../types";

type MarkdownBlock =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "code"; code: string }
  | { type: "table"; rows: string[][] };

function groupPages(pages: WikiPageSummary[]) {
  return pages.reduce<Record<string, WikiPageSummary[]>>((groups, page) => {
    const key = page.type?.trim() || "未分类";
    groups[key] = [...(groups[key] ?? []), page];
    return groups;
  }, {});
}

function splitTableRow(line: string) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableDivider(line: string) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function parseMarkdown(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      blocks.push({ type: "code", code: codeLines.join("\n") });
      index += 1;
      continue;
    }

    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length as 1 | 2 | 3, text: heading[2] });
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ""));
        index += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    if (trimmed.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      const rows = [splitTableRow(line)];
      index += 2;
      while (index < lines.length && lines[index].trim().includes("|") && lines[index].trim() !== "") {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push({ type: "table", rows });
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;
    while (index < lines.length) {
      const next = lines[index].trim();
      if (!next || next.startsWith("```") || /^(#{1,3})\s+/.test(next) || /^[-*]\s+/.test(next)) {
        break;
      }
      if (next.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
        break;
      }
      paragraphLines.push(next);
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

function isSafeMarkdownUrl(url: string) {
  const trimmed = url.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.startsWith("#")) {
    return true;
  }

  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === "http:" || parsed.protocol === "https:" || parsed.protocol === "mailto:";
  } catch {
    return false;
  }
}

function normalizeWikiPath(path: string) {
  const segments: string[] = [];
  for (const segment of path.split("/")) {
    if (!segment || segment === ".") {
      continue;
    }
    if (segment === "..") {
      segments.pop();
      continue;
    }
    segments.push(segment);
  }
  return segments.join("/");
}

function resolveWikiLink(target: string, currentPath: string, pagePaths: Set<string>) {
  const trimmed = target.trim();
  const withoutHash = trimmed.split("#")[0];
  if (!trimmed || trimmed.startsWith("#") || !withoutHash.endsWith(".md")) {
    return null;
  }
  const currentDir = currentPath.includes("/") ? currentPath.slice(0, currentPath.lastIndexOf("/")) : "";
  const candidates = [
    normalizeWikiPath(withoutHash),
    normalizeWikiPath(currentDir ? `${currentDir}/${withoutHash}` : withoutHash)
  ];
  return candidates.find((candidate) => pagePaths.has(candidate)) ?? null;
}

function isLocalEvidenceUrl(url: string) {
  return /(^|\/)(raw|data)\//.test(normalizeWikiPath(url));
}

function renderInlineMarkdown(
  text: string,
  options: {
    currentPath: string;
    pagePaths: Set<string>;
    onSelectPath: (path: string) => void;
  }
): ReactNode[] {
  const parts: ReactNode[] = [];
  const linkPattern = /\[([^\]]+)\]\(([^)\s]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = linkPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const wikiPath = resolveWikiLink(match[2], options.currentPath, options.pagePaths);
    if (wikiPath) {
      parts.push(
        <button
          className="wiki-inline-link"
          key={`${match[2]}-${match.index}`}
          type="button"
          onClick={() => options.onSelectPath(wikiPath)}
        >
          {match[1]}
        </button>
      );
    } else if (isSafeMarkdownUrl(match[2])) {
      parts.push(
        <a href={match[2]} key={`${match[2]}-${match.index}`} rel="noreferrer" target="_blank">
          {match[1]}
        </a>
      );
    } else {
      parts.push(
        <span
          className={isLocalEvidenceUrl(match[2]) ? "local-reference evidence-reference" : "local-reference"}
          key={`${match[2]}-${match.index}`}
          title={match[2]}
        >
          {match[1]}
        </span>
      );
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function MarkdownBody({
  currentPath,
  markdown,
  onSelectPath,
  pagePaths
}: {
  currentPath: string;
  markdown: string;
  onSelectPath: (path: string) => void;
  pagePaths: Set<string>;
}) {
  const blocks = useMemo(() => parseMarkdown(markdown), [markdown]);
  const inlineOptions = useMemo(
    () => ({ currentPath, onSelectPath, pagePaths }),
    [currentPath, onSelectPath, pagePaths]
  );

  if (blocks.length === 0) {
    return <div className="empty-state">暂无正文</div>;
  }

  return (
    <div className="markdown-body">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const Heading = `h${block.level}` as "h1" | "h2" | "h3";
          return <Heading key={index}>{renderInlineMarkdown(block.text, inlineOptions)}</Heading>;
        }
        if (block.type === "list") {
          return (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInlineMarkdown(item, inlineOptions)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "code") {
          return (
            <pre key={index}>
              <code>{block.code}</code>
            </pre>
          );
        }
        if (block.type === "table") {
          const [head, ...body] = block.rows;
          return (
            <div className="markdown-table-wrap" key={index}>
              <table>
                <thead>
                  <tr>
                    {head.map((cell, cellIndex) => (
                      <th key={cellIndex}>{renderInlineMarkdown(cell, inlineOptions)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {body.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex}>{renderInlineMarkdown(cell, inlineOptions)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return <p key={index}>{renderInlineMarkdown(block.text, inlineOptions)}</p>;
      })}
    </div>
  );
}

export function WikiBrowserPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domain, setDomain] = useState("");
  const [pages, setPages] = useState<WikiPageSummary[]>([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [detail, setDetail] = useState<WikiPageDetail | null>(null);
  const [message, setMessage] = useState("");
  const [pageFilter, setPageFilter] = useState("");
  const [loadingPages, setLoadingPages] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getDomains()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setDomains(response);
        setDomain(response[0]?.id ?? "");
        setMessage(response.length === 0 ? "暂无可用 domain" : "");
      })
      .catch((error) => {
        if (!cancelled) {
          setDomains([]);
          setDomain("");
          setMessage(error instanceof Error ? error.message : "加载 domain 失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!domain) {
      setPages([]);
      setSelectedPath("");
      setDetail(null);
      return undefined;
    }

    let cancelled = false;
    setLoadingPages(true);
    setPages([]);
    setSelectedPath("");
    setDetail(null);
    setMessage("");

    getWikiPages(domain)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setPages(response);
        setSelectedPath(response[0]?.path ?? "");
        setMessage(response.length === 0 ? "暂无 wiki 页面" : "");
      })
      .catch((error) => {
        if (!cancelled) {
          setPages([]);
          setSelectedPath("");
          setDetail(null);
          setMessage(error instanceof Error ? error.message : "加载页面失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingPages(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [domain]);

  useEffect(() => {
    if (!domain || !selectedPath) {
      setDetail(null);
      return undefined;
    }

    let cancelled = false;
    setLoadingDetail(true);
    setMessage("");

    getWikiPage(domain, selectedPath)
      .then((response) => {
        if (!cancelled) {
          setDetail(response);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setDetail(null);
          setMessage(error instanceof Error ? error.message : "加载正文失败");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDetail(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [domain, selectedPath]);

  const filteredPages = useMemo(() => {
    const query = pageFilter.trim().toLowerCase();
    if (!query) {
      return pages;
    }
    return pages.filter((page) =>
      [page.title, page.path, page.description, page.type, ...(page.tags ?? [])]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [pageFilter, pages]);
  const groupedPages = useMemo(() => groupPages(filteredPages), [filteredPages]);
  const pagePaths = useMemo(() => new Set(pages.map((page) => page.path)), [pages]);
  const body = detail?.body ?? detail?.content ?? "";
  const tags = detail?.tags ?? [];
  const sourceRefs = detail?.source_refs ?? [];
  const hasDomains = domains.length > 0 && domain !== "";

  return (
    <section className="page-section" aria-labelledby="wiki-browser-title">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Curated Wiki</p>
          <h1 id="wiki-browser-title">Wiki 浏览</h1>
        </div>
        <label className="field-row">
          <span>Domain</span>
          <select
            aria-label="Wiki domain"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            disabled={!hasDomains}
          >
            {domains.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {message && <small role="status">{message}</small>}

      <div className="wiki-browser-grid">
        <aside className="wiki-page-list" aria-label="Wiki 页面列表">
          <label className="wiki-filter">
            <span>过滤页面</span>
            <input
              aria-label="过滤 Wiki 页面"
              placeholder="标题、路径或标签"
              type="search"
              value={pageFilter}
              onChange={(event) => setPageFilter(event.target.value)}
            />
          </label>
          {loadingPages ? <div className="empty-state">正在加载页面</div> : null}
          {!loadingPages && pages.length === 0 ? <div className="empty-state">暂无 wiki 页面</div> : null}
          {!loadingPages && pages.length > 0 && filteredPages.length === 0 ? (
            <div className="empty-state">没有匹配页面</div>
          ) : null}
          {Object.entries(groupedPages).map(([type, group]) => (
            <section className="wiki-page-group" key={type}>
              <h2>{type}</h2>
              {group.map((page) => (
                <button
                  className={`wiki-page-button${page.path === selectedPath ? " active" : ""}`}
                  key={page.path}
                  type="button"
                  onClick={() => setSelectedPath(page.path)}
                >
                  <strong>{page.title || page.path}</strong>
                  <span>{page.path}</span>
                </button>
              ))}
            </section>
          ))}
        </aside>

        <article className="wiki-reader">
          {loadingDetail ? <div className="empty-state">正在加载正文</div> : null}
          {!loadingDetail && detail === null ? <div className="empty-state">请选择页面</div> : null}
          {!loadingDetail && detail !== null ? (
            <>
              <div className="wiki-reader-heading">
                <div>
                  <h2>{detail.title || detail.path}</h2>
                  {detail.description ? <p>{detail.description}</p> : null}
                </div>
              </div>

              <dl className="wiki-metadata">
                <div>
                  <dt>Path</dt>
                  <dd>{detail.path}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{detail.status || "未记录"}</dd>
                </div>
                <div>
                  <dt>Tags</dt>
                  <dd>{tags.length > 0 ? tags.join(", ") : "未标注"}</dd>
                </div>
                <div>
                  <dt>Source refs</dt>
                  <dd>
                    {sourceRefs.length > 0 ? (
                      sourceRefs.map((sourceRef) => <span key={sourceRef}>{sourceRef}</span>)
                    ) : (
                      <span>未记录</span>
                    )}
                  </dd>
                </div>
              </dl>

              <MarkdownBody
                currentPath={detail.path}
                markdown={body}
                onSelectPath={setSelectedPath}
                pagePaths={pagePaths}
              />
            </>
          ) : null}
        </article>
      </div>
    </section>
  );
}
