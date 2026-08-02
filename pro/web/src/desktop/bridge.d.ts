// Ambient declaration of the Electron preload bridge for the React renderer.
// The desktop app injects `window.nexusai`; in a plain browser it is undefined,
// so consumers should feature-detect (see isDesktop()).
import type { DesktopBridge } from "../../../desktop/src/types";

declare global {
  interface Window {
    nexusai?: DesktopBridge;
  }
}
export {};
