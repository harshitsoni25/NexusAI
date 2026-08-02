import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  AreaChart,
  Area,
  Line,
  LineChart,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import KpiCard from "../components/KpiCard";
import ChartCard from "../components/ChartCard";
import type { ReportingBundle } from "../api";

const STATE_COLORS: Record<string, string> = {
  completed: "#15803d",
  failed: "#b91c1c",
  running: "#2563eb",
  other: "#94a3b8",
};

// The Overview section combines Dashboard KPIs, the Success Rate breakdown, and the
// Job Trends time-series — the headline reporting view.
export default function Overview({ bundle }: { bundle: ReportingBundle }) {
  const s = bundle.successRate;
  const pie = [
    { name: "completed", value: s.completed },
    { name: "failed", value: s.failed },
    { name: "running", value: s.running },
    { name: "other", value: s.other },
  ].filter((d) => d.value > 0);

  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {bundle.kpis.map((kpi) => (
          <Grid item xs={6} md={3} key={kpi.id}>
            <KpiCard kpi={kpi} />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <ChartCard title="Success rate" subtitle={`${(s.rate * 100).toFixed(1)}% of ${s.total} jobs completed`}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={2}>
                  {pie.map((d) => (
                    <Cell key={d.name} fill={STATE_COLORS[d.name] ?? "#94a3b8"} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>

        <Grid item xs={12} md={7}>
          <ChartCard title="Job trends" subtitle="Completed vs failed over time">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={bundle.trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="completed" stroke="#15803d" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="failed" stroke="#b91c1c" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>

        <Grid item xs={12}>
          <ChartCard title="Throughput" subtitle="Daily completed jobs" height={220}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={bundle.trends}>
                <defs>
                  <linearGradient id="thru" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="completed" stroke="#0f766e" fill="url(#thru)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
        KPIs, success rate and statistics reflect live engine data when connected; trend, execution-time and storage
        series are illustrative where the backend exposes no time-series endpoint.
      </Typography>
    </Box>
  );
}
