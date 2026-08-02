import { BrowserWindow } from "electron";
import { isDev, preloadPath, RENDERER_DEV_URL, rendererIndexPath } from "./config";
import { hardenWindow } from "./security";

// Creates the single main window with Electron's recommended security settings:
// context isolation on, node integration off, sandboxed renderer, and a preload
// script that is the *only* bridge between the page and the main process.
export function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: "#f6f7f9",
    show: false,
    title: "Nexus AI Pro",
    webPreferences: {
      preload: preloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      spellcheck: false,
    },
  });

  hardenWindow(window);

  window.once("ready-to-show", () => window.show());

  if (isDev) {
    void window.loadURL(RENDERER_DEV_URL);
  } else {
    void window.loadFile(rendererIndexPath());
  }

  return window;
}
