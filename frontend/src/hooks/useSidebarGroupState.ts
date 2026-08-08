"use client";

import * as React from "react";
import type { NavGroupId, NavItem } from "@/lib/navigation";
import { isNavHrefActive } from "@/lib/navigation";

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

function activeGroupId(
  groups: NavGroup[],
  items: NavItem[],
  pathname: string,
  search = "",
): NavGroupId | null {
  if (pathname.startsWith("/apps/") && groups.some((group) => group.id === INSTALLED_APPS_GROUP_ID)) {
    return INSTALLED_APPS_GROUP_ID as NavGroupId;
  }

  const ranked = items
    .filter((item) => isNavHrefActive(pathname, search, item.href))
    .sort((a, b) => b.href.length - a.href.length);
  return ranked[0]?.group ?? null;
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

/** Resolve a single open group: active route wins, else workspace default. */
export function resolveOpenGroupId(
  groups: NavGroup[],
  items: NavItem[],
  pathname: string,
  search = "",
): NavGroupId | null {
  if (groups.length === 0) return null;

  const active = activeGroupId(groups, items, pathname, search);
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
  search = "",
): NavGroupId | null {
  if (groups.length === 0) return null;

  const active = activeGroupId(groups, items, pathname, search);
  if (active && groups.some((group) => group.id === active)) {
    return active;
  }

  return storedOpenGroupId(groups) ?? resolveOpenGroupId(groups, items, pathname, search);
}

export function useSidebarGroupState(
  groups: NavGroup[],
  items: NavItem[],
  pathname: string,
  search = "",
) {
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({});
  const [openGroupId, setOpenGroupId] = React.useState<NavGroupId | null>(null);
  const pathnameRef = React.useRef(pathname);
  const searchRef = React.useRef(search);
  const hydratedRef = React.useRef(false);

  React.useEffect(() => {
    const routeChanged = pathnameRef.current !== pathname || searchRef.current !== search;
    pathnameRef.current = pathname;
    searchRef.current = search;

    const applyOpen = (nextOpen: NavGroupId | null) => {
      setOpenGroupId(nextOpen);
      setExpandedGroups(stateForOpen(groups, nextOpen));
      if (typeof window !== "undefined") {
        persistOpenGroup(groups, nextOpen);
      }
    };

    if (!hydratedRef.current || routeChanged) {
      hydratedRef.current = true;
      applyOpen(resolveHydratedOpenGroupId(groups, items, pathname, search));
      return;
    }

    // Contract/group list refresh: keep the user's open group when it still exists.
    setOpenGroupId((previous) => {
      const stillThere = Boolean(previous && groups.some((group) => group.id === previous));
      const next = (
        stillThere ? previous : resolveHydratedOpenGroupId(groups, items, pathname, search)
      ) as NavGroupId | null;
      setExpandedGroups(stateForOpen(groups, next));
      if (typeof window !== "undefined") {
        persistOpenGroup(groups, next);
      }
      return next;
    });
  }, [groups, items, pathname, search]);

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
        const fallback = resolveOpenGroupId(groups, items, pathname, search);
        return groupId === fallback;
      },
      [expandedGroups, groups, items, pathname, search],
    ),
    toggleGroup,
  };
}
