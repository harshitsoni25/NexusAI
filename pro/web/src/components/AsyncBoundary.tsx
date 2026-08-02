import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import type { ReactNode } from "react";

// Standardises the loading / error / empty states around fetched data.
export default function AsyncBoundary(props: {
  loading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  if (props.loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (props.error) {
    return <Alert severity="error">{props.error}</Alert>;
  }
  return <>{props.children}</>;
}
