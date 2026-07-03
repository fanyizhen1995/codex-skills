import type { Status } from "../types";

const labels: Record<Status, string> = {
  ready: "就绪",
  pending: "等待",
  running: "运行中",
  succeeded: "成功",
  failed: "失败",
  needs_auth_config: "需认证配置",
  auth_failed: "认证失败",
  needs_browser: "需浏览器",
  network_failed: "网络失败",
  unsupported: "不支持",
  trusted: "可信",
  untrusted: "不可信"
};

interface StatusBadgeProps {
  status: Status;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{labels[status]}</span>;
}
