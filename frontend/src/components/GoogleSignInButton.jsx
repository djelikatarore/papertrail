import { useEffect, useRef } from "react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Renders Google's own "Sign in with Google" button via Google Identity
// Services (the script tag in index.html) — not a custom-styled lookalike.
// Google hands back a signed ID token in the callback; this component never
// reads its contents itself, it just forwards the raw token to onToken,
// which POSTs it to the backend for real cryptographic verification.
export default function GoogleSignInButton({ onToken, onError }) {
  const buttonRef = useRef(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      onError?.("Google sign-in is not configured.");
      return undefined;
    }

    let cancelled = false;

    function render() {
      if (cancelled || !buttonRef.current) return;
      if (!window.google?.accounts?.id) {
        // The GIS script loads async — poll briefly until it's ready rather
        // than assuming it's already there on first render.
        setTimeout(render, 100);
        return;
      }
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response) => onToken(response.credential),
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
      });
    }

    render();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={buttonRef} className="flex justify-center" />;
}
