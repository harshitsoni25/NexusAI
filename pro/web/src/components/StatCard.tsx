import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import type { ReactNode } from "react";

// A compact metric tile used across the Dashboard.
export default function StatCard(props: { label: string; value: ReactNode; hint?: string; icon?: ReactNode }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1, color: "text.secondary" }}>
          {props.icon}
          <Typography variant="subtitle2" color="text.secondary">
            {props.label}
          </Typography>
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          {props.value}
        </Typography>
        {props.hint && (
          <Typography variant="caption" color="text.secondary">
            {props.hint}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
