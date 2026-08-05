"use client";

import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";

export const ACCOUNT_NAV_ITEMS = [
  { label: "Overview", href: "/settings/account" },
  { label: "Profile", href: "/settings/account/profile" },
  { label: "Password", href: "/settings/account/password" },
  { label: "Two-factor", href: "/settings/account/two-factor" },
  { label: "Connected accounts", href: "/settings/account/connected-accounts" },
  { label: "Sessions", href: "/settings/account/sessions" },
] as const;

function resolveActive(pathname: string): string {
  const exact = ACCOUNT_NAV_ITEMS.find((item) => pathname === item.href);
  if (exact) {
    return exact.href;
  }
  const nested = ACCOUNT_NAV_ITEMS.find(
    (item) => item.href !== "/settings/account" && pathname.startsWith(`${item.href}/`),
  );
  return nested?.href ?? "/settings/account";
}

export default function AccountNav() {
  const pathname = usePathname();
  const router = useRouter();
  const active = resolveActive(pathname);

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        <FormControl fullWidth size="small">
          <InputLabel id="account-nav-select-label">Account section</InputLabel>
          <Select
            labelId="account-nav-select-label"
            label="Account section"
            value={active}
            onChange={(event) => router.push(String(event.target.value))}
          >
            {ACCOUNT_NAV_ITEMS.map((item) => (
              <MenuItem key={item.href} value={item.href}>
                {item.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      <Tabs
        value={active}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ display: { xs: "none", md: "flex" } }}
      >
        {ACCOUNT_NAV_ITEMS.map((item) => (
          <Tab
            key={item.href}
            label={item.label}
            value={item.href}
            component={NextLink}
            href={item.href}
          />
        ))}
      </Tabs>
    </Box>
  );
}
