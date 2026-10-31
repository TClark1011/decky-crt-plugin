import { Router } from "@decky/ui";
import { setRunningApp } from "~/backend";

// Steam updates MainRunningApp shortly after a lifetime notification, so re-check a few times.
const NOTIFICATION_RECHECK_DELAYS_MS = [500, 2000, 5000];
// Safety net in case a lifetime notification is missed.
const POLL_INTERVAL_MS = 5000;

/**
 * Reports the game currently in focus (or none) to the backend whenever it changes.
 * Returns a function that stops tracking.
 */
export function trackRunningApp(): () => void {
  let lastReportedId: string | null | undefined;

  const report = () => {
    const app = Router.MainRunningApp;
    const id = app ? String(app.appid) : null;
    if (id === lastReportedId) return;
    lastReportedId = id;
    setRunningApp(id, app?.display_name ?? null).catch(() => {
      lastReportedId = undefined;
    });
  };

  const timeouts = new Set<ReturnType<typeof setTimeout>>();
  const registration = SteamClient.GameSessions.RegisterForAppLifetimeNotifications(() => {
    for (const delay of NOTIFICATION_RECHECK_DELAYS_MS) {
      const timeout = setTimeout(() => {
        timeouts.delete(timeout);
        report();
      }, delay);
      timeouts.add(timeout);
    }
  });
  const interval = setInterval(report, POLL_INTERVAL_MS);
  report();

  return () => {
    registration.unregister();
    clearInterval(interval);
    timeouts.forEach(clearTimeout);
  };
}
