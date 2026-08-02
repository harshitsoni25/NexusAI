import { spawn, type ChildProcess } from "node:child_process";
import { BACKEND_ARGS, BACKEND_CMD, SPAWN_BACKEND } from "./config";

// Optionally runs the FastAPI backend as a child process. This *launches* the
// existing backend unchanged — it never modifies it. When SPAWN_BACKEND is false
// (the default), the app assumes an externally running backend or the renderer's
// mock mode, and this manager does nothing.

let child: ChildProcess | null = null;

export function startBackend(): void {
  if (!SPAWN_BACKEND || child) return;
  child = spawn(BACKEND_CMD, BACKEND_ARGS, {
    stdio: "inherit",
    // The backend is launched from wherever its package is importable; packaging can
    // set cwd/env via the environment. No backend files are read or written here.
    env: process.env,
  });
  child.on("exit", (code) => {
    console.log(`[backend] exited with code ${code}`);
    child = null;
  });
}

export function stopBackend(): void {
  if (child) {
    child.kill();
    child = null;
  }
}
