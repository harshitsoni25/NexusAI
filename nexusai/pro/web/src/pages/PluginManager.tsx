import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ListItemIcon from "@mui/material/ListItemIcon";
import Chip from "@mui/material/Chip";
import Alert from "@mui/material/Alert";
import ExtensionIcon from "@mui/icons-material/Extension";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

import PageHeader from "../components/PageHeader";
import AsyncBoundary from "../components/AsyncBoundary";
import { useApi } from "../hooks/useApi";
import { api } from "../api";

export default function PluginManager() {
  const { data, loading, error } = useApi(() => api.plugins(), []);

  return (
    <Box>
      <PageHeader title="Plugin Manager" subtitle="Plugins discovered by the engine at startup" />
      <AsyncBoundary loading={loading} error={error}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Loaded plugins ({data?.count ?? 0})
                </Typography>
                <List>
                  {(data?.loaded ?? []).map((p) => (
                    <ListItem key={p.name} divider secondaryAction={<Chip size="small" color="success" label={p.status ?? "loaded"} />}>
                      <ListItemIcon>
                        <ExtensionIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={p.name} secondary={p.kind ?? "plugin"} />
                    </ListItem>
                  ))}
                  {(data?.loaded ?? []).length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      No plugins loaded.
                    </Typography>
                  )}
                </List>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={5}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Load failures
                </Typography>
                {(data?.failed ?? []).length === 0 ? (
                  <Alert severity="success">No load failures.</Alert>
                ) : (
                  <List>
                    {(data?.failed ?? []).map((f, i) => (
                      <ListItem key={i} divider>
                        <ListItemIcon>
                          <WarningAmberIcon color="warning" />
                        </ListItemIcon>
                        <ListItemText primary={f.detail} />
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </AsyncBoundary>
    </Box>
  );
}
