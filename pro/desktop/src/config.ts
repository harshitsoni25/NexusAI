import { app } from "electron";
import path from "node:path";

// Central configuration. Values can be overridden by environment variables so the
// same build runs in development (Vite dev server + spawned backend) or production
// (packaged renderer + external/sidecar backend) without code changes.

export const isDev = !app.isPackaged;

// Where the renderer (the React app in pro/web) is loaded from.
export const RENDERER_DEV_URL = process.env.NEXUSAI_RENDERER_URL ?? "http://localhost:5173";

// The packaged renderer is copied into resources/renderer at build time
// (see electron-builder.yml extraResources).
export function rendererIndexPath(): string {
  return path.join(process.resourcesPath, "renderer", "index.html");
}

// FastAPI backend the app talks to. The desktop app never modifies the backend; it
// may optionally spawn it as a sidecar (see backend.ts) or use an existing one.
export const BACKEND_URL = process.env.NEXUSAI_BACKEND_URL ?? "http://127.0.0.1:8000";

// Whether to spawn the Python backend as a child process on startup.
export const SPAWN_BACKEND = (process.env.NEXUSAI_SPAWN_BACKEND ?? "false") === "true";

// The command used to launch the backend when SPAWN_BACKEND is enabled. Kept as an
// env-overridable string so packaging can point at a bundled interpreter.
export const BACKEND_CMD = process.env.NEXUSAI_BACKEND_CMD ?? "uvicorn";
export const BACKEND_ARGS = (
  process.env.NEXUSAI_BACKEND_ARGS ?? "nexusai_pro_api.main:app --host 127.0.0.1 --port 8000"
).split(" ");

export const preloadPath = () => path.join(__dirname, "preload.js");
