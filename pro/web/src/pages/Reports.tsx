import { useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ListItemIcon from "@mui/material/ListItemIcon";
import DescriptionIcon from "@mui/icons-material/Description";
import Chip from "@mui/material/Chip";

import PageHeader from "../components/PageHeader";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

const FORMATS = ["html", "json", "pdf"];

export default function Reports() {
  const datasets = useApi(() => api.listDatasets(), []);
  const reports = useApi(() => api.listReports(), []);
  const [datasetId, setDatasetId] = useState("");
  const [format, setFormat] = useState("html");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ severity: "success" | "error"; text: string } | null>(null);

  const generate = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const manifest = await api.createReport(datasetId, format);
      setMessage({ severity: "success", text: `Report generated → ${manifest.location}` });
      reports.reload();
    } catch (err) {
      setMessage({ severity: "error", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader title="Reports" subtitle="Generate and browse dataset reports" />
      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                New report
              </Typography>
              <Stack spacing={2}>
                {message && <Alert severity={message.severity}>{message.text}</Alert>}
                <AsyncBoundary loading={datasets.loading} error={datasets.error}>
                  <TextField select label="Dataset" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} fullWidth>
                    {(datasets.data ?? []).map((d) => (
                      <MenuItem key={d.dataset_id} value={d.dataset_id}>
                        {d.dataset_id} (v{d.version})
                      </MenuItem>
                    ))}
                  </TextField>
                </AsyncBoundary>
                <TextField select label="Format" value={format} onChange={(e) => setFormat(e.target.value)} fullWidth>
                  {FORMATS.map((f) => (
                    <MenuItem key={f} value={f}>
                      {f}
                    </MenuItem>
                  ))}
                </TextField>
                <Button variant="contained" disabled={!datasetId || busy} onClick={generate}>
                  {busy ? "Generating…" : "Generate report"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Generated reports
              </Typography>
              <AsyncBoundary loading={reports.loading} error={reports.error}>
                <List>
                  {(reports.data ?? []).map((r) => (
                    <ListItem key={r.id} divider secondaryAction={<Chip size="small" label={r.format} />}>
                      <ListItemIcon>
                        <DescriptionIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={r.location}
                        secondary={`${r.dataset_id} · ${new Date(r.created_at).toLocaleString()}`}
                        primaryTypographyProps={{ fontFamily: "monospace", fontSize: 14 }}
                      />
                    </ListItem>
                  ))}
                </List>
              </AsyncBoundary>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
