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
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";

import PageHeader from "../components/PageHeader";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api, usingMocks } from "../api";

const FORMATS = ["csv", "json", "ndjson", "excel", "parquet"];

export default function ExportCenter() {
  const datasets = useApi(() => api.listDatasets(), []);
  const exports = useApi(() => api.listExports(), []);
  const [datasetId, setDatasetId] = useState("");
  const [format, setFormat] = useState("csv");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ severity: "success" | "error" | "info"; text: string } | null>(null);

  const create = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const manifest = await api.createExport(datasetId, format);
      setMessage({ severity: "success", text: `Exported ${manifest.dataset_id} → ${manifest.location}` });
      exports.reload();
    } catch (err) {
      setMessage({ severity: "error", text: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader title="Export Center" subtitle="Export datasets to downstream formats" />

      {!usingMocks && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Live backend note: standalone export of a stored dataset returns 501 by design — exports are produced during a
          scrape. This screen still works fully in mock mode.
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                New export
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
                <Button variant="contained" disabled={!datasetId || busy} onClick={create}>
                  {busy ? "Exporting…" : "Create export"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Export history
              </Typography>
              <AsyncBoundary loading={exports.loading} error={exports.error}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Dataset</TableCell>
                      <TableCell>Format</TableCell>
                      <TableCell>Records</TableCell>
                      <TableCell>Location</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(exports.data ?? []).map((e) => (
                      <TableRow key={e.id} hover>
                        <TableCell sx={{ fontFamily: "monospace" }}>{e.dataset_id}</TableCell>
                        <TableCell>
                          <Chip size="small" label={e.format} />
                        </TableCell>
                        <TableCell>{e.record_count}</TableCell>
                        <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{e.location}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </AsyncBoundary>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
