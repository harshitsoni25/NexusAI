// The single source of truth for the IPC contract between the renderer (React app)
// and the Electron main process. Both the preload bridge and the main-process
// handlers import these, so the surface stays whitelisted and typed.

export const Channels = {
  // app / diagnostics
  appInfo: "app:info",
  // native file dialogs
  openFile: "dialog:openFile",
  saveFile: "dialog:saveFile",
  // native downloads
  download: "download:start",
  // native notifications
  notify: "notify:show",
  // shell
  openExternal: "shell:openExternal",
  showItemInFolder: "shell:showItemInFolder",
  // auto-update
  updateCheck: "update:check",
  updateInstall: "update:install",
} as const;

export type ChannelName = (typeof Channels)[keyof typeof Channels];

// main -> renderer events (one-way, sent over a dedicated event channel)
export const Events = {
  downloadProgress: "event:download:progress",
  downloadDone: "event:download:done",
  updateStatus: "event:update:status",
} as const;

export type EventName = (typeof Events)[keyof typeof Events];

export interface AppInfo {
  name: string;
  version: string;
  electron: string;
  chrome: string;
  node: string;
  platform: string;
  backendUrl: string;
}

export interface OpenFileOptions {
  title?: string;
  filters?: { name: string; extensions: string[] }[];
  multiple?: boolean;
}

export interface OpenFileResult {
  canceled: boolean;
  paths: string[];
}

export interface SaveFileOptions {
  title?: string;
  defaultName?: string;
  filters?: { name: string; extensions: string[] }[];
  content?: string; // when provided, main writes it to the chosen path
}

export interface SaveFileResult {
  canceled: boolean;
  path: string | null;
}

export interface DownloadRequest {
  url: string;
  suggestedName?: string;
}

export interface DownloadResult {
  ok: boolean;
  path?: string;
  error?: string;
}

export interface DownloadProgress {
  id: string;
  received: number;
  total: number;
  filename: string;
}

export interface NotifyOptions {
  title: string;
  body: string;
  silent?: boolean;
}

export interface UpdateStatus {
  state: "checking" | "available" | "not-available" | "downloading" | "downloaded" | "error" | "disabled";
  version?: string;
  percent?: number;
  message?: string;
}

// The shape exposed to the renderer via contextBridge as `window.nexusai`.
export interface DesktopBridge {
  appInfo(): Promise<AppInfo>;
  openFile(options?: OpenFileOptions): Promise<OpenFileResult>;
  saveFile(options: SaveFileOptions): Promise<SaveFileResult>;
  download(request: DownloadRequest): Promise<DownloadResult>;
  notify(options: NotifyOptions): Promise<void>;
  openExternal(url: string): Promise<void>;
  showItemInFolder(path: string): Promise<void>;
  checkForUpdates(): Promise<UpdateStatus>;
  installUpdate(): Promise<void>;
  onDownloadProgress(cb: (p: DownloadProgress) => void): () => void;
  onUpdateStatus(cb: (s: UpdateStatus) => void): () => void;
}
