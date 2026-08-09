/** Bridge skin CSS variables to stable --kp-* aliases for non-MUI markup. */

export function syncKeprixCssAliases() {
  if (typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  const dark = root.classList.contains("dark");
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;

  const primary = read("--primary", "#7c3aed");
  const background = read("--background", dark ? "#0a0a0a" : "#ffffff");
  const foreground = read("--foreground", dark ? "#fafafa" : "#111827");
  const muted = read("--muted-foreground", dark ? "#a1a1a1" : "#6b7280");
  const border = read("--border", dark ? "#262626" : "rgba(0, 0, 0, 0.12)");
  const card = read("--card", background);
  const secondary = read("--secondary", "#06b6d4");
  const radius = read("--radius", "0.75rem");

  root.style.setProperty("--kp-primary", primary);
  root.style.setProperty("--kp-primary-light", read("--ring", primary));
  root.style.setProperty("--kp-secondary", secondary);
  root.style.setProperty("--kp-bg", background);
  root.style.setProperty("--kp-bg-paper", card);
  root.style.setProperty("--kp-text-primary", foreground);
  root.style.setProperty("--kp-text-secondary", muted);
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
