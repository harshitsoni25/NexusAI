import { BrowserWindow, dialog } from "electron";
import { writeFile } from "node:fs/promises";
import type {
  OpenFileOptions,
  OpenFileResult,
  SaveFileOptions,
  SaveFileResult,
} from "./types";

// Native OS open/save dialogs, invoked over IPC. The renderer never touches the
// filesystem directly; it asks the main process, which owns all file access.

export async function openFile(
  window: BrowserWindow | null,
  options: OpenFileOptions = {},
): Promise<OpenFileResult> {
  const properties: Array<"openFile" | "multiSelections"> = ["openFile"];
  if (options.multiple) properties.push("multiSelections");

  const result = window
    ? await dialog.showOpenDialog(window, { title: options.title, filters: options.filters, properties })
    : await dialog.showOpenDialog({ title: options.title, filters: options.filters, properties });

  return { canceled: result.canceled, paths: result.filePaths };
}

export async function saveFile(
  window: BrowserWindow | null,
  options: SaveFileOptions,
): Promise<SaveFileResult> {
  const result = window
    ? await dialog.showSaveDialog(window, {
        title: options.title,
        defaultPath: options.defaultName,
        filters: options.filters,
      })
    : await dialog.showSaveDialog({
        title: options.title,
        defaultPath: options.defaultName,
        filters: options.filters,
      });

  if (result.canceled || !result.filePath) {
    return { canceled: true, path: null };
  }

  // When the caller supplies content, persist it to the chosen path.
  if (typeof options.content === "string") {
    await writeFile(result.filePath, options.content, "utf-8");
  }

  return { canceled: false, path: result.filePath };
}
