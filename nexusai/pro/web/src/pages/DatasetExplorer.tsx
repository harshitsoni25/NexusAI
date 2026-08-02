import { useState } from "react";
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import PageHeader from "../components/PageHeader";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

export default function DatasetExplorer() {
  const datasets = useApi(() => api.listDatasets(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const records = useApi(() => (selected ? api.datasetRecords(selected) : Promise.resolve([])), [selected]);

  const columns = records.data && records.data.length > 0 ? Object.keys(records.data[0].fields) : [];

  return (
    <Box>
      <PageHeader title="Dataset Explorer" subtitle="Browse persisted dataset versions and their records" />
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Datasets
              </Typography>
              <AsyncBoundary loading={datasets.loading} error={datasets.error}>
                <List dense disablePadding>
                  {(datasets.data ?? []).map((d) => (
                    <ListItemButton key={d.dataset_id} selected={selected === d.dataset_id} onClick={() => setSelected(d.dataset_id)}>
                      <ListItemText
                        primary={d.dataset_id}
                        secondary={`v${d.version} · ${d.record_count} records · ${d.source_count} sources`}
                        primaryTypographyProps={{ fontFamily: "monospace" }}
                      />
                      {d.quality_grade && <Chip size="small" label={d.quality_grade} color="success" />}
                    </ListItemButton>
                  ))}
                </List>
              </AsyncBoundary>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                {selected ? `Records — ${selected}` : "Select a dataset"}
              </Typography>
              {!selected ? (
                <Typography variant="body2" color="text.secondary">
                  Choose a dataset on the left to inspect its records.
                </Typography>
              ) : (
                <AsyncBoundary loading={records.loading} error={records.error}>
                  <Box sx={{ overflowX: "auto" }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>identity</TableCell>
                          {columns.map((c) => (
                            <TableCell key={c}>{c}</TableCell>
                          ))}
                          <TableCell>source</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(records.data ?? []).map((r) => (
                          <TableRow key={r.identity} hover>
                            <TableCell sx={{ fontFamily: "monospace" }}>{r.identity}</TableCell>
                            {columns.map((c) => (
                              <TableCell key={c}>{r.fields[c]}</TableCell>
                            ))}
                            <TableCell sx={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {r.source_uri}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                </AsyncBoundary>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
