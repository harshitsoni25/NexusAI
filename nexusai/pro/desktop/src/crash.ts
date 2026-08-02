import { app, crashReporter } from "electron";
import fs from "node:fs";
import path from "node:path";

// Crash reporting. Electron's native crashReporter captures native crashes as
// minidumps; an optional upload URL (env NEXUSAI_CRASH_URL, e.g. a Sentry/Crashpad
// endpoint) receives them. Regardless of upload, JS-level uncaught errors are written
// to a local crash log so a field failure is always diagnosable offline.

const CRASH_URL = process.env.NEXUSAI_CRASH_URL ?? "";

export function initCrashReporting(): void {
  crashReporter.start({
    productName: "Nexus AI Pro",
    companyName: "Nexus AI",
    submitURL: CRASH_URL, // empty = collect locally only, do not upload
    uploadToServer: Boolean(CRASH_URL),
    compress: true,
  });

  const logDir = path.join(app.getPath("userData"), "crashes");
  try {
    fs.mkdirSync(logDir, { recursive: true });
  } catch {
    /* best effort */
  }

  const write = (kind: string, err: unknown) => {
    const line = JSON.stringify({
      at: new Date().toISOString(),
      kind,
      message: err instanceof Error ? err.message : String(err),
      stack: err instanceof Error ? err.stack : undefined,
      version: app.getVersion(),
    });
    try {
      fs.appendFileSync(path.join(logDir, "renderer-errors.log"), line + "\n");
    } catch {
      /* best effort */
    }
  };

  process.on("uncaughtException", (err) => write("uncaughtException", err));
  process.on("unhandledRejection", (reason) => write("unhandledRejection", reason));
}

export function crashDirectory(): string {
  return path.join(app.getPath("userData"), "crashes");
}
