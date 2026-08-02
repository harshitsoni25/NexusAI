import { BrowserWindow, dialog, session, type DownloadItem, type Event } from "electron";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { Events, type DownloadProgress, type DownloadRequest, type DownloadResult } from "./types";
import { showNotification } from "./notifications";

// Native download handling. A download can be started programmatically (the renderer
// asks to download a URL) and is also intercepted whenever the page itself triggers
// one. In both cases the main process owns the save location, streams progress to the
// renderer, and raises a native notification on completion.

interface Pending {
  resolve: (result: DownloadResult) => void;
  suggestedName?: string;
}

const pendingByUrl = new Map<string, Pending>();

function emit(window: BrowserWindow | null, channel: string, payload: unknown): void {
  if (window && !window.isDestroyed()) window.webContents.send(channel, payload);
}

/** Wire the session's will-download hook once, at startup. */
export function installDownloadHandler(getWindow: () => BrowserWindow | null): void {
  session.defaultSession.on("will-download", (_event: Event, item: DownloadItem) => {
    const window = getWindow();
    const url = item.getURL();
    const pending = pendingByUrl.get(url);
    const id = randomUUID();
    const suggested = pending?.suggestedName ?? item.getFilename();

    // Ask the user where to save; if they cancel, cancel the download.
    const chosen = dialog.showSaveDialogSync(window ?? undefined as unknown as BrowserWindow, {
      defaultPath: suggested,
    });
    if (!chosen) {
      item.cancel();
      pending?.resolve({ ok: false, error: "canceled" });
      pendingByUrl.delete(url);
      return;
    }
    item.setSavePath(chosen);
    const filename = path.basename(chosen);

    item.on("updated", (_e, state) => {
      if (state === "progressing" && !item.isPaused()) {
        const progress: DownloadProgress = {
          id,
          received: item.getReceivedBytes(),
          total: item.getTotalBytes(),
          filename,
        };
        emit(window, Events.downloadProgress, progress);
      }
    });

    item.once("done", (_e, state) => {
      const ok = state === "completed";
      emit(window, Events.downloadDone, { id, ok, path: ok ? chosen : undefined, filename });
      showNotification({
        title: ok ? "Download complete" : "Download failed",
        body: ok ? filename : `${filename} (${state})`,
      });
      pending?.resolve(ok ? { ok: true, path: chosen } : { ok: false, error: state });
      pendingByUrl.delete(url);
    });
  });
}

/** Programmatically start a download for a URL and resolve when it finishes. */
export function startDownload(window: BrowserWindow | null, request: DownloadRequest): Promise<DownloadResult> {
  return new Promise<DownloadResult>((resolve) => {
    pendingByUrl.set(request.url, { resolve, suggestedName: request.suggestedName });
    if (window && !window.isDestroyed()) {
      window.webContents.downloadURL(request.url);
    } else {
      resolve({ ok: false, error: "no active window" });
      pendingByUrl.delete(request.url);
    }
  });
}
