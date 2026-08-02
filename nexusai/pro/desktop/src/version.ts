import { app } from "electron";
import fs from "node:fs";
import path from "node:path";

// Single source of version/build metadata. At runtime the packaged build-info.json is
// read from resources; in development it is read from the project root. The app version
// always comes from Electron (package.json), keeping one source of truth.

export interface BuildInfo {
  productName: string;
  version: string;
  channel: string;
  commit: string;
  buildDate: string;
  engineDigest: string;
}

let cached: BuildInfo | null = null;

export function buildInfo(): BuildInfo {
  if (cached) return cached;
  const candidates = [
    path.join(process.resourcesPath ?? "", "build-info.json"),
    path.join(__dirname, "..", "build-info.json"),
    path.join(process.cwd(), "build-info.json"),
  ];
  let info: Partial<BuildInfo> = {};
  for (const file of candidates) {
    try {
      info = JSON.parse(fs.readFileSync(file, "utf-8"));
      break;
    } catch {
      /* try next */
    }
  }
  cached = {
    productName: info.productName ?? app.getName(),
    version: app.getVersion() || info.version || "0.0.0",
    channel: info.channel ?? "stable",
    commit: info.commit ?? "unknown",
    buildDate: info.buildDate ?? "unknown",
    engineDigest: info.engineDigest ?? "unknown",
  };
  return cached;
}

export function versionString(): string {
  const b = buildInfo();
  return `${b.version} (${b.channel}) · ${b.commit.slice(0, 7)}`;
}
