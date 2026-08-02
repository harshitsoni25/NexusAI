import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Card from "@mui/material/Card";
import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

import PageHeader from "../components/PageHeader";
import StatusChip from "../components/StatusChip";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

const STATES = ["all", "completed", "running", "failed", "pending", "cancelled"];

export default function JobHistory() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(() => api.listJobs(200), []);
  const [query, setQuery] = useState("");
  const [state, setState] = useState("all");

  const rows = useMemo(() => {
    const jobs = data?.jobs ?? [];
    return jobs.filter((j) => {
      const matchesQuery = !query || (j.target ?? "").toLowerCase().includes(query.toLowerCase()) || j.job_id.includes(query);
      const matchesState = state === "all" || String(j.state) === state;
      return matchesQuery && matchesState;
    });
  }, [data, query, state]);

  return (
    <Box>
      <PageHeader
        title="Job History"
        subtitle="All scraping jobs recorded by the engine"
        actions={
          <Button onClick={reload} variant="outlined">
            Refresh
          </Button>
        }
      />

      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Search target or id"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ minWidth: 260 }}
        />
        <TextField size="small" select label="State" value={state} onChange={(e) => setState(e.target.value)} sx={{ minWidth: 160 }}>
          {STATES.map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      <Card>
        <AsyncBoundary loading={loading} error={error}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Job ID</TableCell>
                  <TableCell>Target</TableCell>
                  <TableCell>Dataset</TableCell>
                  <TableCell>State</TableCell>
                  <TableCell align="right">Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((job) => (
                  <TableRow key={job.job_id} hover>
                    <TableCell sx={{ fontFamily: "monospace" }}>{job.job_id}</TableCell>
                    <TableCell sx={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {job.target ?? "—"}
                    </TableCell>
                    <TableCell sx={{ fontFamily: "monospace" }}>{job.dataset_id ?? "—"}</TableCell>
                    <TableCell>
                      <StatusChip state={String(job.state)} />
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" onClick={() => navigate(`/progress?job=${job.job_id}`)}>
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      No jobs match the current filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </AsyncBoundary>
      </Card>
    </Box>
  );
}
