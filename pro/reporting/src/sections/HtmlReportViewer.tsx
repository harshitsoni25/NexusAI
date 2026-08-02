import { useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import DownloadIcon from "@mui/icons-material/Download";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

// Renders a generated HTML report inside a sandboxed iframe. The sandbox has no
// allow-scripts/allow-same-origin, so report HTML is displayed but cannot run code or
// reach the parent — safe rendering of engine-produced report artifacts.
export default function HtmlReportViewer() {
  const list = useApi(() => api.listReports(), []);
  const [selected, setSelected] = useState<string>("analytics");
  const doc = useApi(() => api.reportDocument(selected), [selected]);

  const download = () => {
    if (!doc.data) return;
    const blob = new Blob([doc.data.html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.data.id}-report.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const openInTab = () => {
    if (!doc.data) return;
    const blob = new Blob([doc.data.html], { type: "text/html" });
    window.open(URL.createObjectURL(blob), "_blank", "noopener");
  };

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
            <AsyncBoundary loading={list.loading} error={list.error}>
              <TextField select size="small" label="Report" value={selected} onChange={(e) => setSelected(e.target.value)} sx={{ minWidth: 240 }}>
                {(list.data ?? []).map((r) => (
                  <MenuItem key={r.id} value={r.id}>{r.title}</MenuItem>
                ))}
              </TextField>
            </AsyncBoundary>
            <Box sx={{ flexGrow: 1 }} />
            <Button startIcon={<OpenInNewIcon />} onClick={openInTab} disabled={!doc.data}>Open</Button>
            <Button variant="contained" startIcon={<DownloadIcon />} onClick={download} disabled={!doc.data}>Download HTML</Button>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <AsyncBoundary loading={doc.loading} error={doc.error}>
          {doc.data && (
            <Box>
              <Box sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", display: "flex", justifyContent: "space-between" }}>
                <Typography variant="subtitle2">{doc.data.title}</Typography>
                <Typography variant="caption" color="text.secondary">generated {new Date(doc.data.generatedAt).toLocaleString()}</Typography>
              </Box>
              <Box
                component="iframe"
                title="report"
                srcDoc={doc.data.html}
                sandbox=""
                sx={{ width: "100%", height: 620, border: 0, display: "block", bgcolor: "#fff" }}
              />
            </Box>
          )}
        </AsyncBoundary>
      </Card>
    </Box>
  );
}
