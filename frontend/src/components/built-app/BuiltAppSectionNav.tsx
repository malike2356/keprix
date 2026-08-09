"use client";

import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { usePathname } from "next/navigation";
import { activeNavItem } from "@/lib/built-app-manifest";
import type { BuiltAppManifest } from "@/components/built-app/types";

type BuiltAppSectionNavProps = {
  manifest: BuiltAppManifest;
};

export default function BuiltAppSectionNav({ manifest }: BuiltAppSectionNavProps) {
  const pathname = usePathname();
  const items = manifest.navigation?.items ?? [];
  const activeItem = activeNavItem(manifest, pathname);

  if (items.length === 0) return null;

  return (
    <Box sx={{ mb: 3, borderBottom: 1, borderColor: "divider", overflowX: "auto" }}>
      <Tabs value={activeItem?.href ?? false} aria-label="App sections" variant="scrollable" scrollButtons="auto">
        {items.map((item) => (
          <Tab
            key={item.id}
            component="a"
            href={item.href}
            value={item.href}
            label={
              item.badge ? (
                <Badge color="primary" badgeContent={item.badge}>
                  <span>{item.label}</span>
                </Badge>
              ) : (
                item.label
              )
            }
            sx={{ minHeight: 44, whiteSpace: "nowrap" }}
          />
        ))}
      </Tabs>
    </Box>
  );
}
