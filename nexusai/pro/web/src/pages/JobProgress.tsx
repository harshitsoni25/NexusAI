import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Stepper from "@mui/material/Stepper";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";

import PageHeader from "../components/PageHeader";
import StatusChip from "../components/StatusChip";
import { api } from "../api";
import type { JobDetail, SubmissionStatus } from "../api";

const STAGES = ["retrieve", "extract", "process", "validate", "persist", "export", "report"];

export default function JobProgress() {
  const [params, setParams] = useSearchParams();
  const submissionId = params.get("submission") ?? "";
  const jobId = params.get("job") ?? "";

  const [submission, setSubmission] = useState<SubmissionStatus | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualId, setManualId] = useState(submissionId || jobId);

  // Poll a submission until it reaches a terminal state.
  useEffect(() => {
    if (!submissionId) return;
    let active = true;
    const tick = async () => {
      try {
        const status = await api.submissionStatus(submissionId);
        if (!active) return;
        setSubmission(status);
        if (status.job_id) {
          const detail = await api.getJob(status.job_id);
          if (active) setJob(detail);
        }
        if (status.state !== "finished" && status.state !== "failed") {
          setTimeout(tick, 1000);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : String(err));
      }
    };
    tick();
    return () => {
      active = false;
    };
  }, [submissionId]);

  // Direct job lookup when navigated with ?job=.
  useEffect(() => {
    if (!jobId) return;
    api
      .getJob(jobId)
      .then(setJob)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [jobId]);

  const state = submission?.state ?? (job ? "finished" : "idle");
  const running = state === "running" || state === "accepted";

  const activeStep = useMemo(() => {
    if (state === "finished" || String(job?.state) === "completed") return STAGES.length;
    if (running) return Math.min(STAGES.length - 1, 3);
    return 0;
  }, [state, job, running]);

  return (
    <Box>
      <PageHeader title="Job Progress" subtitle="Live status of a submission or job" />

      <Card sx={{ mb: 3, maxWidth: 720 }}>
        <CardContent>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              size="small"
              label="Submission or Job ID"
              value={manualId}
              onChange={(e) => setManualId(e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            <button style={{ display: "none" }} />
            <Box
              component="button"
              onClick={() => setParams(manualId.startsWith("job-") ? { job: manualId } : { submission: manualId })}
              sx={{
                px: 2,
                py: 1,
                borderRadius: 1,
                border: "none",
                bgcolor: "primary.main",
                color: "primary.contrastText",
                cursor: "pointer",
              }}
            >
              Track
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!submissionId && !jobId && !error && (
        <Alert severity="info">Enter a submission id (from New Job) or a job id to see progress.</Alert>
      )}

      {(submission || job) && (
        <Card>
          <CardContent>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {submission?.target ?? job?.target ?? "Job"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {submission ? `submission ${submission.submission_id}` : `job ${job?.job_id}`}
                  {job?.job_id && submission?.job_id ? ` → job ${job.job_id}` : ""}
                </Typography>
              </Box>
              <StatusChip state={submission?.state ?? String(job?.state)} />
            </Box>

            {running && <LinearProgress sx={{ mb: 3 }} />}

            <Stepper activeStep={activeStep} alternativeLabel>
              {STAGES.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {submission?.error && (
              <Alert severity="error" sx={{ mt: 3 }}>
                {submission.error}
              </Alert>
            )}

            {job && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Result
                </Typography>
                <pre style={{ margin: 0, fontSize: 13, overflowX: "auto" }}>{JSON.stringify(job.detail, null, 2)}</pre>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
