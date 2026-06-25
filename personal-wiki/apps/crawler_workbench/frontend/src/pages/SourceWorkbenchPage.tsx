import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { StatusBadge } from "../components/StatusBadge";

const coverageData = [
  { name: "RSS", value: 18 },
  { name: "GitHub", value: 9 },
  { name: "Arxiv", value: 7 },
  { name: "Web", value: 5 }
];

const timelineData = [
  { label: "08:00", runs: 4, changed: 2 },
  { label: "10:00", runs: 7, changed: 5 },
  { label: "12:00", runs: 5, changed: 1 },
  { label: "14:00", runs: 9, changed: 4 },
  { label: "16:00", runs: 6, changed: 3 }
];

const topicData = [
  { topic: "平台", rss: 8, github: 5, arxiv: 1, web: 2 },
  { topic: "AI", rss: 3, github: 2, arxiv: 7, web: 1 },
  { topic: "市场", rss: 4, github: 1, arxiv: 0, web: 5 },
  { topic: "安全", rss: 5, github: 4, arxiv: 2, web: 2 }
];

const failureData = [
  { name: "认证失败", value: 5, color: "#b04545" },
  { name: "正文为空", value: 3, color: "#c17a2d" },
  { name: "超时", value: 2, color: "#7a5c28" },
  { name: "格式错误", value: 1, color: "#6b7280" }
];

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

      <div className="panel-grid">
        <div className="work-panel chart-panel">
          <h2>来源覆盖</h2>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={coverageData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} width={34} />
                <Tooltip />
                <Bar dataKey="value" name="来源数" fill="#2f6f73" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>抓取时间线</h2>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} width={34} />
                <Tooltip />
                <Line type="monotone" dataKey="runs" name="抓取" stroke="#2f6f73" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="changed" name="变更" stroke="#7a5c28" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>主题热力</h2>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
                <XAxis dataKey="topic" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} width={34} />
                <Tooltip />
                <Bar dataKey="rss" name="RSS" stackId="topic" fill="#2f6f73" />
                <Bar dataKey="github" name="GitHub" stackId="topic" fill="#4f7f9f" />
                <Bar dataKey="arxiv" name="Arxiv" stackId="topic" fill="#7a5c28" />
                <Bar dataKey="web" name="Web" stackId="topic" fill="#b04545" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="work-panel chart-panel">
          <h2>失败原因分布</h2>
          <div className="chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip />
                <Pie data={failureData} dataKey="value" nameKey="name" outerRadius={82} label>
                  {failureData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  );
}
