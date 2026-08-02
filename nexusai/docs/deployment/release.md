# Release

Cutting a Nexus AI release: version, build, sign, publish, and auto-update.

## Versioning

The desktop app single-sources its version and build metadata:

```bash
cd pro/desktop
npm run version:bump -- <patch|minor|major>   # updates package.json + build-info.json
```

`build-info.json` embeds the version, channel, commit, build date and the engine digest,
surfaced in the About dialog.

## Building artefacts

```bash
(cd pro/web && npm ci && npm run build)        # renderer bundled as the UI
cd pro/desktop && npm ci && npm run release     # package, sign, publish
```

`npm run release` builds all configured targets and publishes the installers together with
the auto-update manifests.

## Code signing

Signing is driven entirely by environment variables — no key material lives in the
repository.

| Platform | Variables |
|---|---|
| Windows (Authenticode) | `CSC_LINK`, `CSC_KEY_PASSWORD` |
| macOS (Developer ID + notarization) | `CSC_LINK`, `CSC_KEY_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` |

macOS builds use the hardened runtime and are notarised after signing; the step is a
no-op when the `APPLE_*` variables are absent, so unsigned local builds still work.

## Auto-update

The app updates itself with an update feed. On launch (and on demand) it queries the feed,
downloads a newer version in the background, and installs it on quit. Updates require a
signed app and an HTTPS feed. Set the release channel with `RELEASE_CHANNEL`
(`stable`, `beta`, `alpha`).

## Pipeline

A tag-triggered pipeline builds, signs and publishes all three platforms — see
[Quality → CI/CD](../quality/ci-cd.md).
