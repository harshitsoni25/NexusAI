import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";

import DashboardIcon from "@mui/icons-material/Dashboard";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import HistoryIcon from "@mui/icons-material/History";
import TimelineIcon from "@mui/icons-material/Timeline";
import StorageIcon from "@mui/icons-material/Storage";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import DescriptionIcon from "@mui/icons-material/Description";
import SettingsIcon from "@mui/icons-material/Settings";
import ArticleIcon from "@mui/icons-material/Article";
import ExtensionIcon from "@mui/icons-material/Extension";
import MenuIcon from "@mui/icons-material/Menu";
import AgricultureIcon from "@mui/icons-material/Agriculture";

import type { ReactNode } from "react";
import { usingMocks } from "../api";

const DRAWER_WIDTH = 240;

export const NAV = [
  { to: "/", label: "Dashboard", icon: <DashboardIcon /> },
  { to: "/new", label: "New Job", icon: <AddCircleOutlineIcon /> },
  { to: "/jobs", label: "Job History", icon: <HistoryIcon /> },
  { to: "/progress", label: "Job Progress", icon: <TimelineIcon /> },
  { to: "/datasets", label: "Dataset Explorer", icon: <StorageIcon /> },
  { to: "/exports", label: "Export Center", icon: <FileDownloadIcon /> },
  { to: "/reports", label: "Reports", icon: <DescriptionIcon /> },
  { to: "/plugins", label: "Plugin Manager", icon: <ExtensionIcon /> },
  { to: "/logs", label: "Logs", icon: <ArticleIcon /> },
  { to: "/settings", label: "Settings", icon: <SettingsIcon /> },
];

export default function Layout({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const drawer = (
    <Box>
      <Toolbar sx={{ gap: 1 }}>
        <AgricultureIcon color="primary" />
        <Typography variant="h6" noWrap>
          Nexus AI Pro
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {NAV.map((item) => {
          const selected =
            item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
          return (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={selected}
              onClick={() => setMobileOpen(false)}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ gap: 1 }}>
          <IconButton
            edge="start"
            onClick={() => setMobileOpen(true)}
            sx={{ display: { md: "none" } }}
            aria-label="open navigation"
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="subtitle1" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {NAV.find((n) => (n.to === "/" ? location.pathname === "/" : location.pathname.startsWith(n.to)))?.label ??
              "Nexus AI Pro"}
          </Typography>
          <Chip
            size="small"
            color={usingMocks ? "warning" : "success"}
            label={usingMocks ? "Mock data" : "Live backend"}
            variant="outlined"
          />
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH, borderRight: 1, borderColor: "divider" },
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` } }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}

export { DRAWER_WIDTH };
export type { ReactNode };
