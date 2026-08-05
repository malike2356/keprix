"use client";

import Box from "@mui/material/Box";
import { usePathname } from "next/navigation";
import BuiltAppHeader from "@/components/built-app/BuiltAppHeader";
import BuiltAppSectionNav from "@/components/built-app/BuiltAppSectionNav";
import BuiltAppSubRail from "@/components/built-app/BuiltAppSubRail";
import type { BuiltAppManifest, BuiltAppNavItem } from "@/components/built-app/types";
import { activeNavItem } from "@/lib/built-app-manifest";

type BuiltAppLayoutProps = {
  manifest: BuiltAppManifest;
  children: React.ReactNode;
  headerActions?: React.ReactNode;
  subRailItems?: BuiltAppNavItem[];
};

export default function BuiltAppLayout({ manifest, children, headerActions, subRailItems }: BuiltAppLayoutProps) {
  const pathname = usePathname();
  const style = manifest.navigation?.style ?? "sections";
  const navItems = manifest.navigation?.items ?? [];
  const railItems = subRailItems ?? navItems;
  const activeItem = activeNavItem(manifest, pathname);

  return (
    <Box sx={{ width: "100%", minWidth: 0 }}>
      <BuiltAppHeader manifest={manifest} activeItem={activeItem} actions={headerActions} />
      {navItems.length > 0 && style !== "tabs_only" ? <BuiltAppSectionNav manifest={manifest} /> : null}
      {style === "sub_rail" ? <BuiltAppSubRail items={railItems}>{children}</BuiltAppSubRail> : children}
    </Box>
  );
}
