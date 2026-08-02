import Chip from "@mui/material/Chip";

const COLORS: Record<string, "success" | "error" | "warning" | "info" | "default"> = {
  completed: "success",
  finished: "success",
  failed: "error",
  running: "info",
  accepted: "info",
  pending: "warning",
  cancelled: "default",
};

// Renders a job/submission state as a coloured chip with consistent semantics.
export default function StatusChip({ state }: { state: string | null | undefined }) {
  const key = (state ?? "unknown").toLowerCase();
  return <Chip size="small" label={state ?? "unknown"} color={COLORS[key] ?? "default"} variant="filled" />;
}
