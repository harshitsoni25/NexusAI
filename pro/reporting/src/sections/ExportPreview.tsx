import { useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";

import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api, type ExportFormat } from "../api";

const FORMATS: ExportFormat[] = ["csv", "json", "ndjson"];

// Previews how an export will look before it is produced: a parsed table view plus the
// raw bytes as they would appear in the file. Reuses the export formats the backend and
// engine already support.
export default function ExportPreview() {
  const datasets = useApi(() => api.datasets(), []);
  const [datasetId, setDatasetId] = useState("ds-a1b2c3");
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [view, setView] = useState<"table" | "raw">("table");
  const preview = useApi(() => api.exportPreview(datasetId, format), [datasetId, format]);

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
            <AsyncBoundary loading={datasets.loading} error={datasets.error}>
              <TextField select size="small" label="Dataset" value={datasetId} onChange={(e) => setDatasetId(e.target.value)} sx={{ minWidth: 200 }}>
                {(datasets.data ?? []).map((d) => (
                  <MenuItem key={d.dataset_id} value={d.dataset_id}>{d.dataset_id} ({d.records})</MenuItem>
                ))}
              </TextField>
            </AsyncBoundary>
            <TextField select size="small" label="Format" value={format} onChange={(e) => setFormat(e.target.value as ExportFormat)} sx={{ minWidth: 140 }}>
              {FORMATS.map((f) => (<MenuItem key={f} value={f}>{f}</MenuItem>))}
            </TextField>
            <Box sx={{ flexGrow: 1 }} />
            <ToggleButtonGroup size="small" exclusive value={view} onChange={(_e, v) => v && setView(v)}>
              <ToggleButton value="table">Table</ToggleButton>
              <ToggleButton value="raw">Raw</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <AsyncBoundary loading={preview.loading} error={preview.error}>
          {preview.data && (
            <Box>
              <Box sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", display: "flex", gap: 1, alignItems: "center" }}>
                <Chip size="small" label={preview.data.format} color="primary" />
                <Typography variant="caption" color="text.secondary">
                  {preview.data.dataset_id} · showing first {preview.data.rows.length} records{preview.data.truncated ? " (truncated)" : ""}
                </Typography>
              </Box>

              {view === "table" ? (
                <Box sx={{ overflowX: "auto" }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        {preview.data.columns.map((c) => (<TableCell key={c}>{c}</TableCell>))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {preview.data.rows.map((r, i) => (
                        <TableRow key={i} hover>
                          {preview.data!.columns.map((c) => (<TableCell key={c}>{r[c]}</TableCell>))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              ) : (
                <Box component="pre" sx={{ m: 0, p: 2, fontSize: 12.5, overflowX: "auto", bgcolor: "#0f172a", color: "#e2e8f0", fontFamily: "monospace" }}>
                  {preview.data.raw}
                </Box>
              )}
            </Box>
          )}
        </AsyncBoundary>
      </Card>
    </Box>
  );
}
