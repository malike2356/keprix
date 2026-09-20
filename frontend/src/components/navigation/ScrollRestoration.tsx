"use client";

import { usePathname } from "next/navigation";
import * as React from "react";

const STORAGE_PREFIX = "keprix:scroll:";

export default function ScrollRestoration() {
  const pathname = usePathname();
  const routeKey = pathname || "/";

  React.useEffect(() => {
    if (!("scrollRestoration" in window.history)) return;
    window.history.scrollRestoration = "manual";

    const storageKey = `${STORAGE_PREFIX}${routeKey}`;
    const main = document.querySelector<HTMLElement>("main");
    const scrollTarget = main && main.scrollHeight > main.clientHeight ? main : null;
    const save = () => {
      const scrollTop = scrollTarget ? scrollTarget.scrollTop : window.scrollY;
      window.sessionStorage.setItem(storageKey, String(scrollTop));
    };
    const restore = () => {
      const saved = window.sessionStorage.getItem(storageKey);
      if (saved === null) return;
      window.requestAnimationFrame(() => {
        if (scrollTarget) scrollTarget.scrollTo({ top: Number(saved), behavior: "auto" });
        else window.scrollTo({ top: Number(saved), behavior: "auto" });
      });
    };

    restore();
    window.addEventListener("pagehide", save);
    window.addEventListener("popstate", restore);
    return () => {
      save();
      window.removeEventListener("pagehide", save);
      window.removeEventListener("popstate", restore);
    };
  }, [routeKey]);

  return null;
}
