"use client";

import BottomNavigation from "@mui/material/BottomNavigation";
import BottomNavigationAction from "@mui/material/BottomNavigationAction";
import Paper from "@mui/material/Paper";
import { usePathname } from "next/navigation";
import NavIcon from "@/components/ui/NavIcon";
import { mobilePrimaryNavigation } from "@/lib/navigation";

export default function MobileBottomNav() {
  const pathname = usePathname();
  const active = mobilePrimaryNavigation.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.href ?? false;
  return (
    <Paper
      elevation={8}
      sx={{
        display: { xs: "block", md: "none" },
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: (theme) => theme.zIndex.appBar,
        borderTop: 1,
        borderColor: "divider",
      }}
    >
      <BottomNavigation
        showLabels
        value={active}
        onChange={(_, value) => {
          window.location.assign(String(value));
        }}
      >
        {mobilePrimaryNavigation.map((item) => (
          <BottomNavigationAction key={item.id} label={item.label} value={item.href} icon={<NavIcon name={item.icon} size={20} />} />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
