import { z } from "zod";
import type { BuiltAppManifest, BuiltAppNavItem } from "@/components/built-app/types";

const builtAppNavItemSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  href: z.string().min(1),
  icon: z.string().optional(),
  badge: z.union([z.string(), z.number()]).optional(),
});

const builtAppManifestSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  description: z.string().optional(),
  entry: z.string().min(1),
  icon: z.string().optional(),
  version: z.string().optional(),
  brand: z
    .object({
      primary_color: z.string().optional(),
    })
    .optional(),
  navigation: z
    .object({
      style: z.enum(["sections", "sub_rail", "tabs_only"]).optional(),
      items: z.array(builtAppNavItemSchema),
    })
    .optional(),
});

function isActiveHref(item: BuiltAppNavItem, pathname: string): boolean {
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function normalizeBuiltAppManifest(raw: unknown): BuiltAppManifest {
  const manifest = builtAppManifestSchema.parse(raw);
  const expectedPrefix = `/apps/${manifest.id}`;

  if (!manifest.entry.startsWith(expectedPrefix)) {
    throw new Error(`Built app entry must start with ${expectedPrefix}`);
  }

  for (const item of manifest.navigation?.items ?? []) {
    if (!item.href.startsWith(expectedPrefix)) {
      throw new Error(`Built app navigation href must start with ${expectedPrefix}`);
    }
  }

  return manifest;
}

export function activeNavItem(manifest: BuiltAppManifest, pathname: string): BuiltAppNavItem | null {
  const items = manifest.navigation?.items ?? [];
  const activeItems = items.filter((item) => isActiveHref(item, pathname));
  if (activeItems.length === 0) return null;
  return activeItems.sort((left, right) => right.href.length - left.href.length)[0];
}
