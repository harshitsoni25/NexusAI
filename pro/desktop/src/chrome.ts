import { BrowserWindow } from "electron";
import path from "node:path";
import { buildInfo, versionString } from "./version";

// Release chrome: the splash window shown while the main window loads, and the About
// dialog. Both are frameless/utility windows with no Node access — pure presentation.

export function createSplashWindow(): BrowserWindow {
  const splash = new BrowserWindow({
    width: 380,
    height: 260,
    frame: false,
    resizable: false,
    center: true,
    show: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  void splash.loadFile(path.join(__dirname, "..", "src", "splash.html"));
  splash.once("ready-to-show", () => splash.show());
  return splash;
}

let aboutWindow: BrowserWindow | null = null;

export function openAboutWindow(parent: BrowserWindow | null): void {
  if (aboutWindow && !aboutWindow.isDestroyed()) {
    aboutWindow.focus();
    return;
  }
  const info = buildInfo();
  const params = new URLSearchParams({
    version: versionString(),
    channel: info.channel,
    commit: info.commit,
    buildDate: info.buildDate,
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
    engine: info.engineDigest.slice(0, 12) + "…",
  });

  aboutWindow = new BrowserWindow({
    width: 460,
    height: 420,
    resizable: false,
    minimizable: false,
    maximizable: false,
    title: "About Nexus AI Pro",
    parent: parent ?? undefined,
    modal: Boolean(parent),
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  void aboutWindow.loadFile(path.join(__dirname, "..", "src", "about.html"), { search: params.toString() });
  aboutWindow.once("ready-to-show", () => aboutWindow?.show());
  aboutWindow.on("closed", () => {
    aboutWindow = null;
  });
}
