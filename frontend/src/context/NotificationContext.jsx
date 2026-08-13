import { createContext, useContext, useEffect, useRef, useState } from "react";
import { getPaper, listMyProcessingPapers } from "../services/paperService";
import { useAuth } from "./AuthContext";

const NotificationContext = createContext(null);

const POLL_INTERVAL_MS = 5000;

// "success" uses amber, not green — the same attention color already used
// for the Processing status pill and WarningBanner, chosen for higher
// visibility than green against this app's mostly-white/purple palette.
const VARIANT_STYLES = {
  success: "border-amber/30 bg-amber-light text-amber",
  error: "border-red/30 bg-red-light text-red",
};

// App-wide watcher for papers finishing background processing — polls a
// lightweight endpoint on an interval regardless of which screen is
// mounted, so a paper started from one screen is still announced even after
// navigating away (unlike the earlier per-page polling this replaces).
// Notifications stay up until manually dismissed (no auto-dismiss timer),
// per an explicit requirement that they not be missed by disappearing too
// soon.
export function NotificationProvider({ children }) {
  const { token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const knownProcessingIds = useRef(new Set());
  const hasPolledOnce = useRef(false);
  const pollRef = useRef(null);

  function dismiss(id) {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }

  function pushNotification(message, variant) {
    const id = Date.now() + Math.random();
    setNotifications((prev) => [...prev, { id, message, variant }]);
  }

  useEffect(() => {
    clearInterval(pollRef.current);
    knownProcessingIds.current = new Set();
    hasPolledOnce.current = false;
    // Not logged in: nothing to watch. This effect re-runs on every token
    // change (login/logout/account switch), so a stale watch from a
    // previous session can never keep running under a new one.
    if (!token) return undefined;

    function poll() {
      listMyProcessingPapers()
        .then((papers) => {
          const currentIds = new Set(papers.map((p) => p.id));

          // The very first poll after mount only seeds the known set — a
          // paper that was already PROCESSING before this tab started
          // watching isn't a "just finished" event we witnessed.
          if (hasPolledOnce.current) {
            const finishedIds = [...knownProcessingIds.current].filter((id) => !currentIds.has(id));
            finishedIds.forEach((id) => {
              getPaper(id)
                .then((paper) => {
                  if (paper.status === "READY") {
                    pushNotification(`"${paper.title ?? paper.filename}" is ready.`, "success");
                  } else if (paper.status === "ERROR") {
                    pushNotification(`"${paper.title ?? paper.filename}" failed to process.`, "error");
                  }
                })
                .catch(() => {});
            });
          }

          knownProcessingIds.current = currentIds;
          hasPolledOnce.current = true;
        })
        .catch(() => {});
    }

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(pollRef.current);
  }, [token]);

  return (
    <NotificationContext.Provider value={{ notifications, dismiss }}>
      {children}
      {notifications.length > 0 && (
        <div className="fixed right-6 top-6 z-[200] flex w-80 flex-col gap-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              role="status"
              className={`flex items-start justify-between gap-3 rounded-xl border px-4 py-3 text-sm font-semibold shadow-card-hover ${VARIANT_STYLES[n.variant]}`}
            >
              <span className="flex-1">{n.message}</span>
              <button
                type="button"
                onClick={() => dismiss(n.id)}
                className="shrink-0 rounded-md border border-current/30 px-2 py-0.5 text-xs font-bold transition-colors hover:bg-current/10"
              >
                OK
              </button>
            </div>
          ))}
        </div>
      )}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
}
