"use client";

import * as React from "react";
import type { NavGroupId, NavItem } from "@/lib/navigation";

const STORAGE_PREFIX = "keprix_nav_group_";
const INSTALLED_APPS_GROUP_ID = "installed_apps";

type NavGroup = {
  id: NavGroupId;
  label: string;
};

export function defaultExpanded(groupId: string, pathname: string): boolean {
  if (groupId === "workspace") return true;
  if (groupId === INSTALLED_APPS_GROUP_ID && pathname.startsWith("/apps/")) return true;
  return false;
}

function storageKey(groupId: string): string {
  return `${STORAGE_PREFIX}${groupId}`;
}

function itemMatchesPath(item: NavItem, pathname: string): boolean {
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function activeGroupId(groups: NavGroup[], items: NavItem[], pathname: string): NavGroupId | null {
  if (pathname.startsWith("/apps/") && groups.some((group) => group.id === INSTALLED_APPS_GROUP_ID)) {
    return INSTALLED_APPS_GROUP_ID as NavGroupId;
  }

  const activeItem = items.find((item) => itemMatchesPath(item, pathname));
  return activeItem?.group ?? null;
}

function persistOpenGroup(groups: NavGroup[], openId: string | null) {
  for (const group of groups) {
    window.localStorage.setItem(storageKey(group.id), group.id === openId ? "1" : "0");
  }
}

function storedOpenGroupId(groups: NavGroup[]): NavGroupId | null {
  if (typeof window === "undefined") return null;
  const storedOpen = groups.find((group) => window.localStorage.getItem(storageKey(group.id)) === "1");
  return storedOpen?.id ?? null;
}

function stateForOpen(groups: NavGroup[], openId: string | null): Record<string, boolean> {
  return groups.reduce<Record<string, boolean>>((state, group) => {
    state[group.id] = group.id === openId;
    return state;
  }, {});
}

/** Accordion toggle: opening one group closes others; toggling the open group collapses it. */
export function nextOpenGroupId(previous: string | null, groupId: string): string | null {
  return previous === groupId ? null : groupId;
}

/** Resolve a single open group: active route wins, else stored, else workspace default. */
export function resolveOpenGroupId(
  groups: NavGroup[],
  items: NavItem[],
  pathname: string,
): NavGroupId | null {
  if (groups.length === 0) return null;

  const active = activeGroupId(groups, items, pathname);
  if (active && groups.some((group) => group.id === active)) {
    return active;
  }

  const workspace = groups.find((group) => group.id === "workspace");
  if (workspace) return workspace.id;

  return groups[0]?.id ?? null;
}

/** Resolve after hydration: active route wins, then stored user preference, then deterministic default. */
export function resolveHydratedOpenGroupId(
  groups: NavGroup[],
  items: NavItem[],
  pathname: string,
): NavGroupId | null {
  if (groups.length === 0) return null;

  const active = activeGroupId(groups, items, pathname);
  if (active && groups.some((group) => group.id === active)) {
    return active;
  }

  return storedOpenGroupId(groups) ?? resolveOpenGroupId(groups, items, pathname);
}

export function useSidebarGroupState(groups: NavGroup[], items: NavItem[], pathname: string) {
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({});
  const [openGroupId, setOpenGroupId] = React.useState<NavGroupId | null>(null);
  const pathnameRef = React.useRef(pathname);
  const hydratedRef = React.useRef(false);

  React.useEffect(() => {
    const routeChanged = pathnameRef.current !== pathname;
    pathnameRef.current = pathname;

    const applyOpen = (nextOpen: NavGroupId | null) => {
      setOpenGroupId(nextOpen);
      setExpandedGroups(stateForOpen(groups, nextOpen));
      if (typeof window !== "undefined") {
        persistOpenGroup(groups, nextOpen);
      }
    };

    if (!hydratedRef.current || routeChanged) {
      hydratedRef.current = true;
      applyOpen(resolveHydratedOpenGroupId(groups, items, pathname));
      return;
    }

    // Contract/group list refresh: keep the user's open group when it still exists.
    setOpenGroupId((previous) => {
      const stillThere = Boolean(previous && groups.some((group) => group.id === previous));
      const next = (stillThere ? previous : resolveHydratedOpenGroupId(groups, items, pathname)) as NavGroupId | null;
      setExpandedGroups(stateForOpen(groups, next));
      if (typeof window !== "undefined") {
        persistOpenGroup(groups, next);
      }
      return next;
    });
  }, [groups, items, pathname]);

  const toggleGroup = React.useCallback(
    (groupId: NavGroupId) => {
      setOpenGroupId((previous) => {
        const next = nextOpenGroupId(previous, groupId) as NavGroupId | null;
        setExpandedGroups(stateForOpen(groups, next));
        if (typeof window !== "undefined") {
          persistOpenGroup(groups, next);
        }
        return next;
      });
    },
    [groups],
  );

  return {
    openGroupId,
    isExpanded: React.useCallback(
      (groupId: NavGroupId) => {
        if (Object.keys(expandedGroups).length > 0) {
          return Boolean(expandedGroups[groupId]);
        }
        // Pre-hydration: show at most the default/active group so multiple groups never flash open.
        const fallback = resolveOpenGroupId(groups, items, pathname);
        return groupId === fallback;
      },
      [expandedGroups, groups, items, pathname],
    ),
    toggleGroup,
  };
}
