// Small helper the React app uses to detect and access the Electron bridge.
import "./bridge.d.ts";

export function isDesktop(): boolean {
  return typeof window !== "undefined" && typeof window.nexusai !== "undefined";
}

export function desktop() {
  return window.nexusai;
}
