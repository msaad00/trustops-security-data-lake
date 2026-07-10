"use client";

import { useEffect, useState } from "react";

/** Screen-reader announcements for SSE platform stream updates (#431). */
export function PlatformStreamLiveRegion() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }
    const es = new EventSource("/api/v1/stream", { withCredentials: true });
    const announce = (label: string) => setMessage(`${label} updated ${new Date().toLocaleTimeString()}`);
    es.addEventListener("posture", () => announce("Posture"));
    es.addEventListener("freshness", () => announce("Evidence freshness"));
    es.addEventListener("audit-readiness", () => announce("Audit readiness"));
    es.addEventListener("ai-governance", () => announce("AI governance"));
    return () => es.close();
  }, []);

  return (
    <div aria-live="polite" aria-atomic="true" className="sr-only">
      {message}
    </div>
  );
}
