#!/usr/bin/env node
// Assembles the self-contained Python runtime that ships inside the Nexus AI desktop app.
//
// It produces two directories under pro/desktop/resources/, which electron-builder copies
// into the packaged app's resources:
//   python/         a relocatable CPython (python-build-standalone) with the Nexus AI
//                   backend stack installed (nexusai engine + nexusai_pro_api + uvicorn +
//                   playwright)
//   ms-playwright/  the Playwright-managed Chromium browser
//
// The end user therefore installs nothing: no system Python, no pip, no browser download.
//
// Run per-OS on the matching CI runner (Windows/macOS/Linux); the interpreter and Chromium
// are platform-specific and cannot be cross-built. Everything here is additive packaging —
// it never modifies the engine or the backend.
//
// Usage:  node scripts/bundle-runtime.mjs
// Env:
//   PBS_PYTHON_VERSION   CPython minor to bundle (default "3.12")
//   PBS_ASSET_URL        pin an exact python-build-standalone asset URL (reproducible CI)
//   PLAYWRIGHT_BROWSER   browser to install (default "chromium")
//   SKIP_BROWSER=1       assemble the interpreter only (used for quick local checks)

import { spawnSync } from "node:child_process";
import { createWriteStream } from "node:fs";
import { mkdir, rm, readdir, stat, access } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import https from "node:https";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DESKTOP = path.resolve(__dirname, "..");
const REPO = path.resolve(DESKTOP, "..", "..");
const RESOURCES = path.join(DESKTOP, "resources");
const PY_DIR = path.join(RESOURCES, "python");
const BROWSERS_DIR = path.join(RESOURCES, "ms-playwright");

const PY_VERSION = process.env.PBS_PYTHON_VERSION ?? "3.12";
const BROWSER = process.env.PLAYWRIGHT_BROWSER ?? "chromium";
const PBS_REPO = "astral-sh/python-build-standalone";

// Pinned, reproducible python-build-standalone release. Builds are deterministic by
// default — the same interpreter ships everywhere. Override PBS_TAG/PBS_PYTHON_FULL to
// move the pin, or set PBS_USE_LATEST=1 to resolve the newest release via the GitHub API.
const PBS_TAG = process.env.PBS_TAG ?? "20241219";
const PBS_PYTHON_FULL = process.env.PBS_PYTHON_FULL ?? "3.12.8";

// platform + arch -> python-build-standalone target triple
function triple() {
  const p = process.platform;
  const a = process.arch;
  const arch = a === "arm64" ? "aarch64" : a === "x64" ? "x86_64" : null;
  if (!arch) throw new Error(`Unsupported arch: ${a}`);
  if (p === "win32") return `${arch}-pc-windows-msvc`;
  if (p === "darwin") return `${arch}-apple-darwin`;
  if (p === "linux") return `${arch}-unknown-linux-gnu`;
  throw new Error(`Unsupported platform: ${p}`);
}

// Path to the bundled interpreter once extracted.
function bundledPython() {
  return process.platform === "win32"
    ? path.join(PY_DIR, "python.exe")
    : path.join(PY_DIR, "bin", "python3");
}

function log(msg) {
  process.stdout.write(`[bundle-runtime] ${msg}\n`);
}

function run(cmd, args, extraEnv = {}) {
  log(`$ ${cmd} ${args.join(" ")}`);
  const res = spawnSync(cmd, args, {
    stdio: "inherit",
    env: { ...process.env, ...extraEnv },
    shell: false,
  });
  if (res.status !== 0) {
    throw new Error(`Command failed (${res.status}): ${cmd} ${args.join(" ")}`);
  }
}

function getJSON(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "nexusai-bundler", Accept: "application/vnd.github+json" } }, (res) => {
        if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return resolve(getJSON(res.headers.location));
        }
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => {
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            reject(e);
          }
        });
      })
      .on("error", reject);
  });
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    log(`downloading ${url}`);
    https
      .get(url, { headers: { "User-Agent": "nexusai-bundler" } }, (res) => {
        if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          return resolve(download(res.headers.location, dest));
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
        }
        const out = createWriteStream(dest);
        res.pipe(out);
        out.on("finish", () => out.close(() => resolve(dest)));
        out.on("error", reject);
      })
      .on("error", reject);
  });
}

// Resolve the python-build-standalone asset URL for this platform.
async function resolveAssetUrl() {
  if (process.env.PBS_ASSET_URL) return process.env.PBS_ASSET_URL;
  const want = triple();

  // Default: deterministic, pinned release built as a direct download URL (no API call,
  // so no rate limits and fully reproducible).
  if (process.env.PBS_USE_LATEST !== "1") {
    const name = `cpython-${PBS_PYTHON_FULL}+${PBS_TAG}-${want}-install_only.tar.gz`;
    return `https://github.com/${PBS_REPO}/releases/download/${PBS_TAG}/${name}`;
  }

  // Opt-in: resolve the newest release via the GitHub API (uses GITHUB_TOKEN in CI).
  log(`resolving latest python-build-standalone asset for ${want} (CPython ${PY_VERSION}.x)`);
  const release = await getJSON(`https://api.github.com/repos/${PBS_REPO}/releases/latest`);
  const assets = release.assets ?? [];
  const match = assets.find(
    (x) =>
      x.name.startsWith(`cpython-${PY_VERSION}.`) &&
      x.name.includes(want) &&
      x.name.endsWith("install_only.tar.gz")
  );
  if (!match) {
    throw new Error(
      `No install_only asset for CPython ${PY_VERSION}.x / ${want}. Pin one via PBS_ASSET_URL.`
    );
  }
  return match.browser_download_url;
}

async function exists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function assembleInterpreter() {
  await rm(PY_DIR, { recursive: true, force: true });
  await mkdir(RESOURCES, { recursive: true });
  const url = await resolveAssetUrl();
  const archive = path.join(tmpdir(), `python-runtime-${Date.now()}.tar.gz`);
  await download(url, archive);

  // python-build-standalone install_only archives unpack to a top-level "python/" dir.
  log(`extracting into ${RESOURCES}`);
  run("tar", ["-xzf", archive, "-C", RESOURCES]);
  await rm(archive, { force: true });

  const py = bundledPython();
  if (!(await exists(py))) throw new Error(`Interpreter missing after extraction: ${py}`);
  run(py, ["--version"]);
  return py;
}

async function installBackend(py) {
  log("installing the Nexus AI backend stack into the bundled interpreter");
  run(py, ["-m", "pip", "install", "--upgrade", "pip"]);
  // The engine and the API are local packages; pip resolves the api's `nexusai`
  // dependency from the engine path provided on the same command line. uvicorn, fastapi
  // and pydantic come in as the api's dependencies.
  run(py, ["-m", "pip", "install", "--no-cache-dir", REPO, path.join(REPO, "pro", "api"), "playwright"]);
}

async function installBrowser(py) {
  if (process.env.SKIP_BROWSER === "1") {
    log("SKIP_BROWSER=1 — skipping Chromium download");
    return;
  }
  await rm(BROWSERS_DIR, { recursive: true, force: true });
  await mkdir(BROWSERS_DIR, { recursive: true });
  log(`installing Playwright ${BROWSER} into ${BROWSERS_DIR}`);
  // PLAYWRIGHT_BROWSERS_PATH makes Playwright place browsers in our bundle rather than the
  // user's home. The same variable is set at runtime (see src/config.ts) so the app finds
  // exactly this Chromium.
  run(py, ["-m", "playwright", "install", BROWSER], { PLAYWRIGHT_BROWSERS_PATH: BROWSERS_DIR });
}

async function prune() {
  // Trim caches to keep the installer smaller. Only removes regenerable bytecode/caches.
  log("pruning caches");
  async function walk(dir) {
    let entries;
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (e.name === "__pycache__" || e.name === ".pytest_cache") {
          await rm(full, { recursive: true, force: true });
        } else {
          await walk(full);
        }
      }
    }
  }
  await walk(PY_DIR);
}

async function report() {
  async function dirSize(dir) {
    let total = 0;
    async function walk(d) {
      let entries;
      try {
        entries = await readdir(d, { withFileTypes: true });
      } catch {
        return;
      }
      for (const e of entries) {
        const full = path.join(d, e.name);
        if (e.isDirectory()) await walk(full);
        else {
          try {
            total += (await stat(full)).size;
          } catch {
            /* ignore */
          }
        }
      }
    }
    await walk(dir);
    return total;
  }
  const mb = (b) => (b / 1024 / 1024).toFixed(1);
  log(`python runtime:  ${mb(await dirSize(PY_DIR))} MB`);
  if (await exists(BROWSERS_DIR)) log(`bundled browser: ${mb(await dirSize(BROWSERS_DIR))} MB`);
}

async function main() {
  log(`platform=${process.platform} arch=${process.arch} triple=${triple()}`);
  const py = await assembleInterpreter();
  await installBackend(py);
  await installBrowser(py);
  await prune();
  await report();
  log("runtime bundle complete → resources/python, resources/ms-playwright");
}

main().catch((err) => {
  console.error(`[bundle-runtime] FAILED: ${err.message}`);
  process.exit(1);
});
