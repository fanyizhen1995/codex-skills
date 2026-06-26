import type { WikiGraphEdge, WikiGraphNode } from "../types";

interface WikiGraphProps {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
}

const nodeColors: Record<string, string> = {
  note: "#2f6f73",
  topic: "#4f7f9f",
  domain: "#7a5c28",
  source: "#b04545"
};

function nodeLabel(node: WikiGraphNode) {
  return node.title ?? node.path ?? node.id;
}

export function WikiGraph({ nodes, edges }: WikiGraphProps) {
  if (nodes.length === 0) {
    return (
      <div style={{ height: 360, display: "grid", placeItems: "center", color: "#66757b" }}>
        暂无关系数据
      </div>
    );
  }

  const width = 720;
  const height = 360;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.34;
  const positions = new Map(
    nodes.map((node, index) => {
      const angle = nodes.length === 1 ? -Math.PI / 2 : (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
      return [
        node.id,
        {
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius
        }
      ];
    })
  );

  return (
    <svg role="img" aria-label="知识关系图" viewBox={`0 0 ${width} ${height}`} width="100%" height="360">
      <rect width={width} height={height} rx="8" fill="#f8fafb" />
      {edges.map((edge, index) => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) {
          return null;
        }
        return (
          <line
            key={`${edge.source}-${edge.target}-${index}`}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke="#b8c4ca"
            strokeWidth="1.4"
          />
        );
      })}
      {nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) {
          return null;
        }
        const label = nodeLabel(node);
        return (
          <g key={node.id} transform={`translate(${position.x} ${position.y})`}>
            <circle r="13" fill={nodeColors[node.type ?? ""] ?? "#6b7280"} stroke="#ffffff" strokeWidth="3">
              <title>{`${label}${node.type ? ` (${node.type})` : ""}`}</title>
            </circle>
            <text y="29" textAnchor="middle" fill="#172026" fontSize="12">
              {label.length > 18 ? `${label.slice(0, 17)}...` : label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
