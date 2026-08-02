import { useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";

import PageHeader from "../components/PageHeader";
import { usingMocks } from "../api";

// Settings are presentation-only here: they configure the client. The data mode
// (mock vs live) is fixed at build time via VITE_USE_MOCKS and shown read-only.
export default function Settings() {
  const [apiBase, setApiBase] = useState(import.meta.env.VITE_API_BASE ?? "/api/v1");
  const [maxConcurrent, setMaxConcurrent] = useState(4);
  const [logJson, setLogJson] = useState(true);
  const [saved, setSaved] = useState(false);

  return (
    <Box>
      <PageHeader title="Settings" subtitle="Client and backend connection preferences" />
      <Card sx={{ maxWidth: 720 }}>
        <CardContent>
          <Stack spacing={3}>
            {saved && <Alert severity="success">Preferences saved for this session.</Alert>}

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Data source
              </Typography>
              <Chip
                color={usingMocks ? "warning" : "success"}
                label={usingMocks ? "Mock data (VITE_USE_MOCKS=true)" : "Live backend"}
                variant="outlined"
              />
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Switch modes by setting VITE_USE_MOCKS and rebuilding.
              </Typography>
            </Box>

            <Divider />

            <TextField
              label="API base path"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
              fullWidth
              helperText="Where the SPA calls the FastAPI backend (proxied in dev)."
            />
            <TextField
              label="Max concurrent scrapes (display)"
              type="number"
              value={maxConcurrent}
              onChange={(e) => setMaxConcurrent(Number(e.target.value))}
              sx={{ maxWidth: 280 }}
            />
            <FormControlLabel
              control={<Switch checked={logJson} onChange={(e) => setLogJson(e.target.checked)} />}
              label="Structured JSON logs"
            />

            <Box>
              <Button variant="contained" onClick={() => setSaved(true)}>
                Save preferences
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
