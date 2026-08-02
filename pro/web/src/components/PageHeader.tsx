import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

// A consistent title/subtitle/actions row at the top of each screen.
export default function PageHeader(props: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <Box sx={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", mb: 3, gap: 2, flexWrap: "wrap" }}>
      <Box>
        <Typography variant="h5">{props.title}</Typography>
        {props.subtitle && (
          <Typography variant="body2" color="text.secondary">
            {props.subtitle}
          </Typography>
        )}
      </Box>
      {props.actions}
    </Box>
  );
}
