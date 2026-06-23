from __future__ import annotations

import json
from pathlib import Path
import sys
from xml.sax.saxutils import escape

try:
    from . import graph
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph  # type: ignore


def generate_html(root: Path, domain: str | None, out: Path) -> Path:
    data = graph.build_graph(root, domain)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render_html(data), encoding="utf-8")
    return out


def _render_html(data: dict[str, object]) -> str:
    graph_json = _safe_script_json(data)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Personal Wiki Graph</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --accent: #0b57d0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      padding: 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      font-weight: 700;
    }}
    main {{
      display: grid;
      gap: 24px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      padding: 24px;
    }}
    section {{
      min-width: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    ul {{
      list-style: none;
      margin: 0;
      padding: 0;
      border: 1px solid var(--line);
      background: var(--panel);
    }}
    li {{
      padding: 12px 14px;
      border-top: 1px solid var(--line);
    }}
    li:first-child {{ border-top: 0; }}
    .title {{ font-weight: 650; }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .edge {{
      color: var(--accent);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Personal Wiki Graph</h1>
    <div class="meta">{len(nodes)} nodes, {len(edges)} edges</div>
  </header>
  <main>
    <section>
      <h2>Nodes</h2>
      <ul id="nodes">
{_node_items(nodes)}
      </ul>
    </section>
    <section>
      <h2>Edges</h2>
      <ul id="edges">
{_edge_items(edges)}
      </ul>
    </section>
  </main>
  <script>
    const graphData = {graph_json};
    window.personalWikiGraph = graphData;
  </script>
</body>
</html>
"""


def _node_items(nodes: object) -> str:
    if not isinstance(nodes, list):
        return ""
    return "\n".join(_node_item(node) for node in nodes if isinstance(node, dict))


def _node_item(node: dict[object, object]) -> str:
    title = _escape_html(str(node.get("title") or node.get("id") or "Untitled"))
    node_id = _escape_html(str(node.get("id") or ""))
    description = _escape_html(str(node.get("description") or ""))
    return (
        '        <li><div class="title">'
        f"{title}</div><div class=\"meta\">{node_id}</div>"
        f'<div class="meta">{description}</div></li>'
    )


def _edge_items(edges: object) -> str:
    if not isinstance(edges, list):
        return ""
    return "\n".join(_edge_item(edge) for edge in edges if isinstance(edge, dict))


def _edge_item(edge: dict[object, object]) -> str:
    source = _escape_html(str(edge.get("source") or ""))
    target = _escape_html(str(edge.get("target") or ""))
    return f'        <li><div class="edge">{source} -> {target}</div></li>'


def _escape_html(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&#x27;"})


def _safe_script_json(data: object) -> str:
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
