# Desktop

The desktop app is a hardened Electron shell around the web UI, with native integration,
a splash screen, an About dialog, crash reporting and auto-update.

## Installers

Prebuilt installers are published per platform:

| Platform | Artefact |
|---|---|
| Windows | NSIS `Setup` installer (x64, arm64) |
| macOS | `.dmg` and `.zip` (x64, arm64), hardened runtime + notarised |
| Linux | `.AppImage`, `.deb`, `.rpm` |

## Building locally

```bash
cd pro/desktop
npm ci
npm run build              # compile
npm run dist:win           # or dist:mac / dist:linux
```

Artefacts are written to `pro/desktop/release/`.

## Configuration

The desktop app can launch a local backend sidecar and connect to it:

```bash
export NEXUSAI_SPAWN_BACKEND=true
export NEXUSAI_BACKEND_URL=http://127.0.0.1:8000
```

See the [Environment reference](../api/environment.md#desktop) for all desktop variables.

## Security

The renderer runs with context isolation and sandboxing enabled and node integration
disabled, behind a strict content-security policy. Only a whitelisted preload bridge is
exposed. Report viewers render untrusted HTML in an empty-sandbox iframe.

## Auto-update

Signed builds check the release feed on launch and via **Help → Check for Updates**, then
install on quit. See [Release](release.md).
