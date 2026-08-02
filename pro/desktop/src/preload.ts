import { contextBridge, ipcRenderer } from "electron";
import { Channels, Events } from "./types";
import type {
  AppInfo,
  DesktopBridge,
  DownloadProgress,
  DownloadRequest,
  DownloadResult,
  NotifyOptions,
  OpenFileOptions,
  OpenFileResult,
  SaveFileOptions,
  SaveFileResult,
  UpdateStatus,
} from "./types";

// The preload runs in an isolated context with Node access, but the page does not.
// It exposes ONLY the functions below on `window.nexusai` via contextBridge —
// never `ipcRenderer` itself — so the renderer can invoke a fixed, audited set of
// channels and nothing more. Event subscriptions are wrapped so the raw event object
// is never handed to the page.

function subscribe<T>(channel: string, cb: (payload: T) => void): () => void {
  const listener = (_event: unknown, payload: T) => cb(payload);
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
}

const bridge: DesktopBridge = {
  appInfo: () => ipcRenderer.invoke(Channels.appInfo) as Promise<AppInfo>,
  openFile: (options?: OpenFileOptions) =>
    ipcRenderer.invoke(Channels.openFile, options) as Promise<OpenFileResult>,
  saveFile: (options: SaveFileOptions) =>
    ipcRenderer.invoke(Channels.saveFile, options) as Promise<SaveFileResult>,
  download: (request: DownloadRequest) =>
    ipcRenderer.invoke(Channels.download, request) as Promise<DownloadResult>,
  notify: (options: NotifyOptions) => ipcRenderer.invoke(Channels.notify, options) as Promise<void>,
  openExternal: (url: string) => ipcRenderer.invoke(Channels.openExternal, url) as Promise<void>,
  showItemInFolder: (path: string) =>
    ipcRenderer.invoke(Channels.showItemInFolder, path) as Promise<void>,
  checkForUpdates: () => ipcRenderer.invoke(Channels.updateCheck) as Promise<UpdateStatus>,
  installUpdate: () => ipcRenderer.invoke(Channels.updateInstall) as Promise<void>,
  onDownloadProgress: (cb: (p: DownloadProgress) => void) => subscribe(Events.downloadProgress, cb),
  onUpdateStatus: (cb: (s: UpdateStatus) => void) => subscribe(Events.updateStatus, cb),
};

contextBridge.exposeInMainWorld("nexusai", bridge);
