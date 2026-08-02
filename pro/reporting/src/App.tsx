import { useState } from "react";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Button from "@mui/material/Button";
import RefreshIcon from "@mui/icons-material/Refresh";
import InsightsIcon from "@mui/icons-material/Insights";

import { useApi } from "./hooks/useApi";
import { api, usingMocks, type RangeKey } from "./api";
import AsyncBoundary from "./components/AsyncBoundary";
import Overview from "./sections/Overview";
import Performance from "./sections/Performance";
import Statistics from "./sections/Statistics";
import HtmlReportViewer from "./sections/HtmlReportViewer";
import ExportPreview from "./sections/ExportPreview";

const RANGES: { value: RangeKey; label: string }[] = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
];

export default function App() {
  const [tab, setTab] = useState(0);
  const [range, setRange] = useState<RangeKey>("30d");
  const bundle = useApi(() => api.bundle(range), [range]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 1 }}>
          <InsightsIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>Nexus AI Pro — Reporting</Typography>
          <Chip size="small" variant="outlined" color={usingMocks ? "warning" : "success"} label={usingMocks ? "Mock data" : "Live backend"} sx={{ ml: 1 }} />
          <Box sx={{ flexGrow: 1 }} />
          <TextField select size="small" value={range} onChange={(e) => setRange(e.target.value as RangeKey)} sx={{ minWidth: 150 }}>
            {RANGES.map((r) => (<MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>))}
          </TextField>
          <Button startIcon={<RefreshIcon />} onClick={bundle.reload}>Refresh</Button>
        </Toolbar>
        <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ px: 2 }}>
          <Tab label="Overview" />
          <Tab label="Performance" />
          <Tab label="Statistics" />
          <Tab label="Report Viewer" />
          <Tab label="Export Preview" />
        </Tabs>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {tab <= 2 ? (
          <AsyncBoundary loading={bundle.loading} error={bundle.error}>
            {bundle.data && tab === 0 && <Overview bundle={bundle.data} />}
            {bundle.data && tab === 1 && <Performance bundle={bundle.data} />}
            {bundle.data && tab === 2 && <Statistics bundle={bundle.data} />}
          </AsyncBoundary>
        ) : tab === 3 ? (
          <HtmlReportViewer />
        ) : (
          <ExportPreview />
        )}
      </Container>
    </Box>
  );
}
