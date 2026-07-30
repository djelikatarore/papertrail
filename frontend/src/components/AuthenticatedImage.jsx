import { useEffect, useState } from "react";
import apiClient from "../services/apiClient";

// Figure images require the same JWT auth as every other API call, but a
// plain <img src> can't attach an Authorization header — fetch the bytes via
// apiClient (which does attach it) and hand the browser an object URL instead.
export default function AuthenticatedImage({ src, alt, className }) {
  const [objectUrl, setObjectUrl] = useState(null);

  useEffect(() => {
    let currentUrl = null;
    let cancelled = false;

    apiClient
      .get(src, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        currentUrl = URL.createObjectURL(res.data);
        setObjectUrl(currentUrl);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [src]);

  if (!objectUrl) {
    return <div className={`animate-pulse bg-border ${className ?? ""}`} />;
  }

  return <img src={objectUrl} alt={alt} className={className} />;
}
