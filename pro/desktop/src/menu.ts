import { app, Menu, shell, type BrowserWindow } from "electron";
import { checkForUpdates } from "./updater";

// The application menu. Beyond the platform standards it exposes "About Nexus AI Pro"
// and "Check for Updates" so the About dialog and the update pipeline are reachable
// from the UI. No functional scraping features are added here.
export function buildMenu(openAbout: () => void, getWindow: () => BrowserWindow | null): void {
  const isMac = process.platform === "darwin";

  const template: Electron.MenuItemConstructorOptions[] = [
    ...(isMac
      ? [{
          label: app.getName(),
          submenu: [
            { label: "About Nexus AI Pro", click: () => openAbout() },
            { label: "Check for Updates…", click: () => void checkForUpdates() },
            { type: "separator" as const },
            { role: "services" as const },
            { type: "separator" as const },
            { role: "hide" as const },
            { role: "quit" as const },
          ],
        }]
      : []),
    { role: "fileMenu" },
    { role: "editMenu" },
    { role: "viewMenu" },
    { role: "windowMenu" },
    {
      role: "help",
      submenu: [
        { label: "Documentation", click: () => void shell.openExternal("https://github.com/your-org/nexusai-pro") },
        { label: "Check for Updates…", click: () => void checkForUpdates() },
        ...(!isMac ? [{ label: "About Nexus AI Pro", click: () => openAbout() }] : []),
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  void getWindow; // reserved for future window-scoped items
}
