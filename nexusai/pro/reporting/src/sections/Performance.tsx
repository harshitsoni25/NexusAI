import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import ChartCard from "../components/ChartCard";
import type { ReportingBundle } from "../api";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ textAlign: "center", px: 2 }}>
      <Typography variant="h5">{value}</Typography>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
    </Box>
  );
}

// Execution Time (latency distribution + percentiles) and Storage Usage (growth over
// time and by dataset).
export default function Performance({ bundle }: { bundle: ReportingBundle }) {
  const e = bundle.executionTime;
  const st = bundle.storage;
  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <ChartCard title="Execution time" subtitle="Distribution of job durations">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={e.histogram}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#0f766e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
        <Grid item xs={12} md={5}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>Latency percentiles</Typography>
              <Stack direction="row" justifyContent="space-around">
                <Stat label="p50" value={`${e.p50}s`} />
                <Stat label="p90" value={`${e.p90}s`} />
                <Stat label="p99" value={`${e.p99}s`} />
              </Stack>
              <Box sx={{ mt: 3, textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">Average</Typography>
                <Typography variant="h6">{e.averageSeconds}s</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <ChartCard title="Storage usage" subtitle={`${st.totalMb.toFixed(0)} MB across datasets, exports and reports`}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={st.points}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="datasetsMb" stackId="1" stroke="#0f766e" fill="#0f766e" fillOpacity={0.5} name="datasets" />
                <Area type="monotone" dataKey="exportsMb" stackId="1" stroke="#b45309" fill="#b45309" fillOpacity={0.5} name="exports" />
                <Area type="monotone" dataKey="reportsMb" stackId="1" stroke="#2563eb" fill="#2563eb" fillOpacity={0.5} name="reports" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
        <Grid item xs={12} md={4}>
          <ChartCard title="Storage by dataset" subtitle="Largest datasets">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={st.byDataset} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="dataset_id" width={90} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="mb" fill="#0f766e" radius={[0, 6, 6, 0]} name="MB" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
}
