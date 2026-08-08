"use client";

import * as React from "react";

/** Honor prefers-reduced-motion with optional user override (prompt 514). */
export function useReducedMotion(userOverride?: boolean | null) {
  const [prefers, setPrefers] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setPrefers(mq.matches);
    update();
    mq.addEventListener?.("change", update);
    return () => mq.removeEventListener?.("change", update);
  }, []);

  if (userOverride === true) return true;
  if (userOverride === false) return false;
  return prefers;
}

export default useReducedMotion;
