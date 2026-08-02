import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import { Link as RouterLink } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

import WorkOutlineIcon from "@mui/icons-material/WorkOutline";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HealthAndSafetyIcon from "@mui/icons-material/HealthAndSafety";

import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import StatusChip from "../components/StatusChip";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

const PIE_COLORS = ["#0f766e", "#b45309", "#b91c1c", "#2563eb", "#7c3aed"];

export default function Dashboard() {
  const stats = useApi(() => api.statistics(), []);
  const jobs = useApi(() => api.listJobs(5), []);
  const ready = useApi(() => api.readiness(), []);

  const byState = stats.data?.by_state ?? {};
  const chartData = Object.entries(byState).map(([state, count]) => ({ state, count }));
  const completed = byState["completed"] ?? 0;
  const failed = byState["failed"] ?? 0;

  return (
    <Box>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of scraping activity and engine health"
        actions={
          <Button component={RouterLink} to="/new" variant="contained" startIcon={<WorkOutlineIcon />}>
            New Job
          </Button>
        }
      />

      <AsyncBoundary loading={stats.loading} error={stats.error}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <StatCard label="Total jobs" value={stats.data?.total_jobs ?? 0} icon={<WorkOutlineIcon fontSize="small" />} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard label="Completed" value={completed} icon={<CheckCircleOutlineIcon fontSize="small" />} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard label="Failed" value={failed} icon={<ErrorOutlineIcon fontSize="small" />} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatCard
              label="Engine"
              value={ready.data?.ready ? "Ready" : ready.loading ? "…" : "Check"}
              hint="doctor readiness"
              icon={<HealthAndSafetyIcon fontSize="small" />}
            />
          </Grid>
        </Grid>
      </AsyncBoundary>

      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Jobs by state
              </Typography>
              <Box sx={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <XAxis dataKey="state" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#0f766e" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                State distribution
              </Typography>
              <Box sx={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData} dataKey="count" nameKey="state" outerRadius={90} label>
                      {chartData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                <Typography variant="subtitle2">Recent jobs</Typography>
                <Button component={RouterLink} to="/jobs" size="small">
                  View all
                </Button>
              </Box>
              <AsyncBoundary loading={jobs.loading} error={jobs.error}>
                {(jobs.data?.jobs ?? []).map((job) => (
                  <Box
                    key={job.job_id}
                    sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", py: 1, borderTop: 1, borderColor: "divider" }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" noWrap>
                        {job.target ?? job.job_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {job.job_id}
                      </Typography>
                    </Box>
                    <StatusChip state={String(job.state)} />
                  </Box>
                ))}
              </AsyncBoundary>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
