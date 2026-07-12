"use client";

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Stack from "@mui/material/Stack";
import Link from "next/link";

type BrainSectionTabsProps = {
  value: "graph" | "galaxy" | "list" | "health";
};

export default function BrainSectionTabs({ value }: BrainSectionTabsProps) {
  return (
    <Stack direction="row" alignItems="center" spacing={1} sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}>
      <Tabs value={value} sx={{ minHeight: 44 }} variant="scrollable" allowScrollButtonsMobile>
        <Tab label="Graph" value="graph" component={Link} href="/brain/graph" sx={{ minHeight: 44 }} />
        <Tab label="Galaxy" value="galaxy" component={Link} href="/memory/galaxy" sx={{ minHeight: 44 }} />
        <Tab label="List" value="list" component={Link} href="/memory" sx={{ minHeight: 44 }} />
        <Tab label="Health" value="health" component={Link} href="/brain/health" sx={{ minHeight: 44 }} />
      </Tabs>
    </Stack>
  );
}
