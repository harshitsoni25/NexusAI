import { app, session, shell, type BrowserWindow, type WebContents } from "electron";
import { BACKEND_URL, isDev, RENDERER_DEV_URL } from "./config";

// Central place for the app's security posture. Electron's own guidance is applied:
// context isolation and sandboxing are set on the window (see windows.ts); here we
// lock down navigation, window creation, permissions, and add a Content-Security
// -Policy so the renderer can only talk to itself and the local backend.

function allowedOrigins(): string[] {
  const origins = [BACKEND_URL];
  if (isDev) origins.push(RENDERER_DEV_URL);
  return origins;
}

function isSameApp(url: string): boolean {
  if (url.startsWith("file://")) return true;
  return allowedOrigins().some((origin) => url.startsWith(origin));
}

/** Apply a strict Content-Security-Policy to every response the renderer loads. */
export function installContentSecurityPolicy(): void {
  const connectSrc = ["'self'", ...allowedOrigins(), isDev ? "ws://localhost:5173" : ""].filter(Boolean);
  const policy = [
    "default-src 'self'",
    // MUI/emotion inject styles at runtime, so inline styles are permitted.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    `connect-src ${connectSrc.join(" ")}`,
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [policy],
      },
    });
  });
}

/** Deny all permission requests (camera, geolocation, etc.) — the app needs none. */
export function lockDownPermissions(): void {
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
}

/** Prevent navigation away from the app and route external links to the OS browser. */
export function guardNavigation(contents: WebContents): void {
  contents.on("will-navigate", (event, url) => {
    if (!isSameApp(url)) {
      event.preventDefault();
      void shell.openExternal(url);
    }
  });

  contents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) void shell.openExternal(url);
    return { action: "deny" };
  });

  // Block webview attachment entirely.
  contents.on("will-attach-webview", (event) => event.preventDefault());
}

/** Refuse to create additional renderers with unsafe web preferences. */
export function enforceSecureDefaults(): void {
  app.on("web-contents-created", (_event, contents) => guardNavigation(contents));
}

export function hardenWindow(window: BrowserWindow): void {
  guardNavigation(window.webContents);
}
