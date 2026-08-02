import { Notification } from "electron";
import type { NotifyOptions } from "./types";

// Shows a native OS notification. Guards on Notification.isSupported() so calls are
// safe on platforms/environments without notification support.
export function showNotification(options: NotifyOptions): void {
  if (!Notification.isSupported()) return;
  const notification = new Notification({
    title: options.title,
    body: options.body,
    silent: options.silent ?? false,
  });
  notification.show();
}
