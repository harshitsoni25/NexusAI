import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";

import PageHeader from "../components/PageHeader";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";
import type { LogEntry } from "../api";

const LEVELS = ["ALL", "INFO", "WARNING", "ERROR", "DEBUG"];
const LEVEL_COLOR: Record<string, "default" | "info" | "warning" | "error"> = {
  INFO: "info",
  WARNING: "warning",
  ERROR: "error",
  DEBUG: "default",
};

export default function Logs() {
  const { data, loading, error, reload } = useApi(() => api.logs(), []);
  const [level, setLevel] = useState("ALL");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    const logs: LogEntry[] = data ?? [];
    return logs.filter(
      (l) =>
        (level === "ALL" || l.level === level) &&
        (!query || l.message.toLowerCase().includes(query.toLowerCase()) || l.logger.includes(query)),
    );
  }, [data, level, query]);

  return (
    <Box>
      <PageHeader
        title="Logs"
        subtitle="Structured log stream from the API and engine"
        actions={
          <Button variant="outlined" onClick={reload}>
            Refresh
          </Button>
        }
      />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
        <TextField size="small" label="Search" value={query} onChange={(e) => setQuery(e.target.value)} sx={{ minWidth: 260 }} />
        <TextField size="small" select label="Level" value={level} onChange={(e) => setLevel(e.target.value)} sx={{ minWidth: 140 }}>
          {LEVELS.map((l) => (
            <MenuItem key={l} value={l}>
              {l}
            </MenuItem>
          ))}
        </TextField>
      </Stack>
      <Card>
        <AsyncBoundary loading={loading} error={error}>
          <TableContainer sx={{ maxHeight: 560 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Level</TableCell>
                  <TableCell>Logger</TableCell>
                  <TableCell>Message</TableCell>
                  <TableCell>Request</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((l, i) => (
                  <TableRow key={i} hover>
                    <TableCell sx={{ whiteSpace: "nowrap", fontFamily: "monospace", fontSize: 12 }}>
                      {new Date(l.timestamp).toLocaleTimeString()}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={l.level} color={LEVEL_COLOR[l.level] ?? "default"} />
                    </TableCell>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{l.logger}</TableCell>
                    <TableCell>{l.message}</TableCell>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{l.request_id}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </AsyncBoundary>
      </Card>
    </Box>
  );
}
