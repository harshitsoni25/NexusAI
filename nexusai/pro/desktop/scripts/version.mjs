#!/usr/bin/env node
// Version management: bump the desktop app version and regenerate build-info.json with
// the current git commit and build date. Usage: node scripts/version.mjs <patch|minor|major|X.Y.Z>
import { readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";

const arg = process.argv[2] ?? "patch";
const pkgPath = new URL("../package.json", import.meta.url);
const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));

function bump(version, kind) {
  if (/^\d+\.\d+\.\d+$/.test(kind)) return kind;
  const [maj, min, pat] = version.split(".").map(Number);
  if (kind === "major") return `${maj + 1}.0.0`;
  if (kind === "minor") return `${maj}.${min + 1}.0`;
  return `${maj}.${min}.${pat + 1}`;
}

const next = bump(pkg.version, arg);
pkg.version = next;
writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");

let commit = "unknown";
try { commit = execSync("git rev-parse --short HEAD").toString().trim(); } catch {}

const channel = process.env.RELEASE_CHANNEL ?? "stable";
const info = {
  productName: pkg.productName ?? "Nexus AI Pro",
  version: next,
  channel,
  commit,
  buildDate: new Date().toISOString(),
  engineDigest: "c940b7fb5a5675fa4d466356d0479582b39c9fc5c64b9b1e64593071b00fc112",
};
writeFileSync(new URL("../build-info.json", import.meta.url), JSON.stringify(info, null, 2) + "\n");
console.log(`version -> ${next} (${channel}, ${commit})`);
