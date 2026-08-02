import { app, type BrowserWindow } from "electron";
import { autoUpdater } from "electron-updater";
import { Events, type UpdateStatus } from "./types";

// Auto-update readiness via electron-updater. The updater is fully wired — status is
// streamed to the renderer and the app can check/download/install — but it only does
// anything when the app is packaged and a publish feed is configured (see
// electron-builder.yml). In development, or without a feed, calls resolve to a
// "disabled" status rather than throwing.

let mainWindow: BrowserWindow | null = null;

function push(status: UpdateStatus): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(Events.updateStatus, status);
  }
}

export function initUpdater(window: BrowserWindow): void {
  mainWindow = window;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("checking-for-update", () => push({ state: "checking" }));
  autoUpdater.on("update-available", (info) => push({ state: "available", version: info.version }));
  autoUpdater.on("update-not-available", () => push({ state: "not-available" }));
  autoUpdater.on("download-progress", (p) => push({ state: "downloading", percent: Math.round(p.percent) }));
  autoUpdater.on("update-downloaded", (info) => push({ state: "downloaded", version: info.version }));
  autoUpdater.on("error", (err) => push({ state: "error", message: err.message }));
}

function updatesEnabled(): boolean {
  // Updates only make sense for a packaged app with a configured publish feed.
  return app.isPackaged;
}

export async function checkForUpdates(): Promise<UpdateStatus> {
  if (!updatesEnabled()) {
    const status: UpdateStatus = { state: "disabled", message: "Updates run in the packaged app with a publish feed." };
    push(status);
    return status;
  }
  try {
    const result = await autoUpdater.checkForUpdates();
    const version = result?.updateInfo?.version;
    return version ? { state: "available", version } : { state: "not-available" };
  } catch (err) {
    return { state: "error", message: err instanceof Error ? err.message : String(err) };
  }
}

export function installUpdate(): void {
  if (updatesEnabled()) autoUpdater.quitAndInstall();
}
