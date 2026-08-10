/** Bridge skin CSS variables to stable --kp-* aliases for non-MUI markup. */

import { ensureMutedText, ensurePrimaryText } from "./contrast";

export function syncKeprixCssAliases() {
  if (typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  const dark = root.classList.contains("dark");
  const mode = dark ? "dark" : "light";
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;

  const primary = read("--primary", "#7c3aed");
  const background = read("--background", dark ? "#0a0a0a" : "#ffffff");
  const foregroundRaw = read("--foreground", dark ? "#fafafa" : "#111827");
  const mutedRaw = read("--muted-foreground", dark ? "#d1d5db" : "#374151");
  const border = read("--border", dark ? "#262626" : "rgba(0, 0, 0, 0.12)");
  const card = read("--card", background);
  const paper = card || background;
  const secondary = read("--secondary", "#06b6d4");
  const radius = read("--radius", "0.75rem");
  const foreground = ensurePrimaryText(foregroundRaw, paper, mode);
  const muted = ensureMutedText(mutedRaw, paper, mode);

  root.style.setProperty("--kp-primary", primary);
  root.style.setProperty("--kp-primary-light", read("--ring", primary));
  root.style.setProperty("--kp-secondary", secondary);
  root.style.setProperty("--kp-bg", background);
  root.style.setProperty("--kp-bg-paper", card);
  root.style.setProperty("--kp-text-primary", foreground);
  root.style.setProperty("--kp-text-secondary", muted);
  // Keep raw skin vars aligned so Tailwind / CSS utilities using --muted-foreground stay readable.
  root.style.setProperty("--muted-foreground", muted);
  root.style.setProperty("--foreground", foreground);
  root.style.setProperty("--card-foreground", foreground);
  root.style.setProperty("--kp-border", border);
  root.style.setProperty("--kp-radius-card", radius);
  root.style.setProperty("--kp-radius-chip", "9999px");
}

export function pulseSkinChange() {
  if (typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  root.classList.add("keprix-skin-pulse");
  window.setTimeout(() => root.classList.remove("keprix-skin-pulse"), 420);
}
