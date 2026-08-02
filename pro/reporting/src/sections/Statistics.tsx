import Card from "@mui/material/Card";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import type { ReportingBundle } from "../api";

// The full statistics table — every computed metric, live where derivable.
export default function Statistics({ bundle }: { bundle: ReportingBundle }) {
  return (
    <Card>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Metric</TableCell>
              <TableCell align="right">Value</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {bundle.statistics.map((row) => (
              <TableRow key={row.metric} hover>
                <TableCell>{row.metric}</TableCell>
                <TableCell align="right" sx={{ fontFamily: "monospace" }}>{row.value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}
