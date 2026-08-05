"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import type { BuiltAppNavItem } from "@/components/built-app/types";

type BuiltAppSubRailProps = {
  items: BuiltAppNavItem[];
  children: React.ReactNode;
};

export default function BuiltAppSubRail({ items, children }: BuiltAppSubRailProps) {
  const pathname = usePathname();

  return (
    <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 3, alignItems: "stretch" }}>
      <Box
        component="nav"
        aria-label="App sub navigation"
        sx={{
          width: { xs: "100%", md: 220 },
          flexShrink: 0,
          borderRight: { xs: 0, md: 1 },
          borderBottom: { xs: 1, md: 0 },
          borderColor: "divider",
          pr: { xs: 0, md: 2 },
          pb: { xs: 2, md: 0 },
        }}
      >
        <List dense disablePadding>
          {items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <ListItemButton
                key={item.id}
                component={NextLink}
                href={item.href}
                selected={active}
                sx={{ borderRadius: 1 }}
              >
                <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2" }} />
                {item.badge ? <Chip size="small" label={item.badge} /> : null}
              </ListItemButton>
            );
          })}
        </List>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>{children}</Box>
    </Box>
  );
}
