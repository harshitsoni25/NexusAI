import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";

import PageHeader from "../components/PageHeader";
import { api } from "../api";
import type { ScrapeAccepted } from "../api";

const EXPORT_FORMATS = ["csv", "json", "ndjson"];
const REPORT_FORMATS = ["html", "json"];

export default function NewJob() {
  const navigate = useNavigate();
  const [target, setTarget] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [exportFormats, setExportFormats] = useState<string[]>(["csv", "json"]);
  const [reportFormats, setReportFormats] = useState<string[]>(["html"]);
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState<ScrapeAccepted | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = (list: string[], setList: (v: string[]) => void, value: string) =>
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const result = await api.startScrape({
        target: target.trim(),
        dataset_id: datasetId.trim() || undefined,
        export_formats: exportFormats,
        report_formats: reportFormats,
      });
      setAccepted(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const validUrl = /^https?:\/\/.+/i.test(target.trim());

  return (
    <Box>
      <PageHeader title="New Job" subtitle="Start a scraping workflow against a target" />
      <Card sx={{ maxWidth: 720 }}>
        <CardContent>
          {accepted ? (
            <Stack spacing={2}>
              <Alert severity="success">
                Scrape accepted — submission <strong>{accepted.submission_id}</strong> ({accepted.state}).
              </Alert>
              <Typography variant="body2" color="text.secondary">
                Dataset <code>{accepted.dataset_id}</code>. Track progress on the Job Progress screen.
              </Typography>
              <Stack direction="row" spacing={1}>
                <Button variant="contained" onClick={() => navigate(`/progress?submission=${accepted.submission_id}`)}>
                  Track progress
                </Button>
                <Button
                  onClick={() => {
                    setAccepted(null);
                    setTarget("");
                    setDatasetId("");
                  }}
                >
                  New another
                </Button>
              </Stack>
            </Stack>
          ) : (
            <Stack spacing={3}>
              {error && <Alert severity="error">{error}</Alert>}
              <TextField
                label="Target URL"
                placeholder="https://example.com/products"
                fullWidth
                required
                value={target}
                error={target.length > 0 && !validUrl}
                helperText={target.length > 0 && !validUrl ? "Enter an http(s) URL" : "The page or endpoint to scrape"}
                onChange={(e) => setTarget(e.target.value)}
              />
              <TextField
                label="Dataset ID (optional)"
                placeholder="Derived from the target when blank"
                fullWidth
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
              />

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Export formats
                </Typography>
                <FormGroup row>
                  {EXPORT_FORMATS.map((f) => (
                    <FormControlLabel
                      key={f}
                      control={<Checkbox checked={exportFormats.includes(f)} onChange={() => toggle(exportFormats, setExportFormats, f)} />}
                      label={f}
                    />
                  ))}
                </FormGroup>
              </Box>

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Report formats
                </Typography>
                <FormGroup row>
                  {REPORT_FORMATS.map((f) => (
                    <FormControlLabel
                      key={f}
                      control={<Checkbox checked={reportFormats.includes(f)} onChange={() => toggle(reportFormats, setReportFormats, f)} />}
                      label={f}
                    />
                  ))}
                </FormGroup>
              </Box>

              <Box>
                <Button variant="contained" size="large" disabled={!validUrl || submitting} onClick={submit}>
                  {submitting ? "Submitting…" : "Start scrape"}
                </Button>
              </Box>
            </Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
