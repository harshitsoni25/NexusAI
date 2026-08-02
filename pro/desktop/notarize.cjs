// electron-builder afterSign hook: notarize the macOS app.
// Runs only on macOS and only when Apple credentials are present, so it is a safe
// no-op on other platforms and in unsigned local builds.
const { notarize } = require("@electron/notarize");

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== "darwin") return;

  const appleId = process.env.APPLE_ID;
  const appleIdPassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;
  if (!appleId || !appleIdPassword || !teamId) {
    console.log("[notarize] Apple credentials not set — skipping notarization.");
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  console.log(`[notarize] Submitting ${appName} for notarization…`);
  await notarize({
    appBundleId: "com.nexusai.pro",
    appPath: `${appOutDir}/${appName}.app`,
    appleId,
    appleIdPassword,
    teamId,
  });
  console.log("[notarize] Done.");
};
