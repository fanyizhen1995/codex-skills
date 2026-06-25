import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export interface TrendPoint {
  label: string;
  fetched: number;
  changed: number;
  failed: number;
}

interface TrendChartProps {
  data: TrendPoint[];
}

export function TrendChart({ data }: TrendChartProps) {
  return (
    <div className="chart-frame" role="img" aria-label="抓取趋势">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 18, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="#e5ebef" strokeDasharray="3 3" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} />
          <YAxis tickLine={false} axisLine={false} width={36} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="fetched" name="抓取" stroke="#2f6f73" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="changed" name="变更" stroke="#7a5c28" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="failed" name="失败" stroke="#b04545" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
