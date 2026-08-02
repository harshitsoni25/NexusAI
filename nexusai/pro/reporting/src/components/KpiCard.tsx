import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import type { Kpi } from "../api";

// A single KPI tile with an optional period-over-period delta.
export default function KpiCard({ kpi }: { kpi: Kpi }) {
  const up = (kpi.delta ?? 0) >= 0;
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary">{kpi.label}</Typography>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5 }}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>{kpi.value}</Typography>
          {kpi.unit && <Typography variant="subtitle1" color="text.secondary">{kpi.unit}</Typography>}
        </Box>
        {kpi.delta !== undefined && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.25, color: up ? "success.main" : "error.main" }}>
            {up ? <ArrowUpwardIcon sx={{ fontSize: 14 }} /> : <ArrowDownwardIcon sx={{ fontSize: 14 }} />}
            <Typography variant="caption">{Math.abs(kpi.delta)}%</Typography>
            <Typography variant="caption" color="text.secondary">vs prev</Typography>
          </Box>
        )}
        {kpi.hint && !kpi.delta && <Typography variant="caption" color="text.secondary">{kpi.hint}</Typography>}
      </CardContent>
    </Card>
  );
}
