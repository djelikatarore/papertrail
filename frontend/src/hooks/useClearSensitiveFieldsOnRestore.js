import { useEffect } from "react";

// Browser back/forward-cache (bfcache) can restore a page — including its
// live React state — exactly as the user left it, bypassing a normal
// remount. Without this, a filled-in email/password can silently reappear
// after navigating away and back via the browser's back button. `pageshow`
// with `event.persisted === true` is the standard signal a page came from
// bfcache rather than a fresh load.
export default function useClearSensitiveFieldsOnRestore(clearFields) {
  useEffect(() => {
    function handlePageShow(event) {
      if (event.persisted) {
        clearFields();
      }
    }
    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
