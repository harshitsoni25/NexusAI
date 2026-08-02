import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import type { ReactNode } from "react";

// A titled container that gives every chart a consistent frame and height.
export default function ChartCard(props: { title: string; subtitle?: string; height?: number; actions?: ReactNode; children: ReactNode }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
          <Box>
            <Typography variant="subtitle2">{props.title}</Typography>
            {props.subtitle && <Typography variant="caption" color="text.secondary">{props.subtitle}</Typography>}
          </Box>
          {props.actions}
        </Box>
        <Box sx={{ height: props.height ?? 260 }}>{props.children}</Box>
      </CardContent>
    </Card>
  );
}
