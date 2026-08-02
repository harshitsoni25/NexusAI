import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0f766e" },
    secondary: { main: "#b45309" },
    background: { default: "#f6f7f9", paper: "#ffffff" },
    success: { main: "#15803d" }, warning: { main: "#b45309" }, error: { main: "#b91c1c" },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`, h5: { fontWeight: 700 }, h6: { fontWeight: 700 }, subtitle2: { fontWeight: 600 } },
  components: { MuiCard: { defaultProps: { variant: "outlined" } }, MuiButton: { defaultProps: { disableElevation: true } } },
});
