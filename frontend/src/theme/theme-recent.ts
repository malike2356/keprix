import type { ThemeSkin } from "@/components/providers/ThemeRegistry";

const RECENT_KEY = "keprix_theme_skin_recent";
const MAX_RECENT = 5;

export function readRecentSkinIds(): string[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((id): id is string => typeof id === "string");
  } catch {
    return [];
  }
}

export function rememberSkinId(skinId: string) {
  if (typeof window === "undefined" || !skinId) {
    return;
  }
  const next = [skinId, ...readRecentSkinIds().filter((id) => id !== skinId)].slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function pickRandomSkinId(currentSkinId: string, skins: ThemeSkin[]): string {
  const pool = skins.filter((skin) => skin.id !== currentSkinId);
  if (!pool.length) {
    return currentSkinId;
  }
  return pool[Math.floor(Math.random() * pool.length)].id;
}
