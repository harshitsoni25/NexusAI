import { app, BrowserWindow } from "electron";
import { SPAWN_BACKEND } from "./config";
import {
  enforceSecureDefaults,
  installContentSecurityPolicy,
  lockDownPermissions,
} from "./security";
import { createMainWindow } from "./windows";
import { registerIpc } from "./ipc";
import { installDownloadHandler } from "./downloads";
import { initUpdater, checkForUpdates } from "./updater";
import { startBackend, stopBackend } from "./backend";
import { initCrashReporting } from "./crash";
import { createSplashWindow, openAboutWindow } from "./chrome";
import { buildMenu } from "./menu";

// The main process. Order matters: crash reporting and security defaults are
// established before any window exists, IPC and the download handler are registered
// once, and the optional backend sidecar is started before the window loads so the
// API is reachable. A splash window covers startup until the main window is ready.

let mainWindow: BrowserWindow | null = null;
const getWindow = () => mainWindow;

// A single instance keeps one backend sidecar and one window.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  // Crash reporting must start before the app is ready so early crashes are captured.
  initCrashReporting();

  enforceSecureDefaults();

  app.whenReady().then(() => {
    installContentSecurityPolicy();
    lockDownPermissions();
    installDownloadHandler(getWindow);
    registerIpc(getWindow);

    if (SPAWN_BACKEND) startBackend();

    // Show the splash while the main window loads, then swap.
    const splash = createSplashWindow();

    mainWindow = createMainWindow();
    initUpdater(mainWindow);
    buildMenu(() => openAboutWindow(getWindow()), getWindow);

    mainWindow.once("ready-to-show", () => {
      if (!splash.isDestroyed()) splash.close();
    });

    // A non-blocking update check on launch (no-op unless packaged with a feed).
    void checkForUpdates();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        mainWindow = createMainWindow();
        initUpdater(mainWindow);
      }
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  app.on("before-quit", () => stopBackend());
}
