import { app, BrowserWindow, ipcMain, shell } from "electron";
import { Channels } from "./types";
import type {
  AppInfo,
  DownloadRequest,
  NotifyOptions,
  OpenFileOptions,
  SaveFileOptions,
} from "./types";
import { BACKEND_URL } from "./config";
import { openFile, saveFile } from "./dialogs";
import { showNotification } from "./notifications";
import { startDownload } from "./downloads";
import { checkForUpdates, installUpdate } from "./updater";

// Registers exactly the channels declared in the IPC contract. Every handler runs in
// the main process; the renderer can only reach them through the preload bridge.
// Using ipcMain.handle (request/response) keeps the surface explicit and auditable.
export function registerIpc(getWindow: () => BrowserWindow | null): void {
  ipcMain.handle(Channels.appInfo, (): AppInfo => {
    return {
      name: app.getName(),
      version: app.getVersion(),
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      platform: process.platform,
      backendUrl: BACKEND_URL,
    };
  });

  ipcMain.handle(Channels.openFile, (_e, options: OpenFileOptions = {}) => openFile(getWindow(), options));
  ipcMain.handle(Channels.saveFile, (_e, options: SaveFileOptions) => saveFile(getWindow(), options));

  ipcMain.handle(Channels.download, (_e, request: DownloadRequest) => startDownload(getWindow(), request));

  ipcMain.handle(Channels.notify, (_e, options: NotifyOptions) => {
    showNotification(options);
  });

  ipcMain.handle(Channels.openExternal, (_e, url: string) => {
    if (/^https?:\/\//.test(url)) return shell.openExternal(url);
    return Promise.resolve();
  });
  ipcMain.handle(Channels.showItemInFolder, (_e, filePath: string) => {
    shell.showItemInFolder(filePath);
  });

  ipcMain.handle(Channels.updateCheck, () => checkForUpdates());
  ipcMain.handle(Channels.updateInstall, () => {
    installUpdate();
  });
}
