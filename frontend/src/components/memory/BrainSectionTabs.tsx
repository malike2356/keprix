"use client";

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Box from "@mui/material/Box";

type BrainSectionTabsProps = {
  value: "graph" | "galaxy" | "list" | "health";
};

export default function BrainSectionTabs({ value }: BrainSectionTabsProps) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 0 }}>
      <Tabs
        value={value}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{
          minHeight: 36,
          "& .MuiTab-root": {
            minHeight: 36,
            textTransform: "none",
            fontWeight: 500,
            color: "text.secondary",
            px: 1.25,
            py: 0,
          },
          "& .Mui-selected": {
            color: "text.primary",
            fontWeight: 600,
          },
          "& .MuiTabs-indicator": {
            height: 2,
            borderRadius: 1,
          },
        }}
      >
        <Tab label="Graph" value="graph" component="a" href="/brain/graph" />
        <Tab label="Galaxy" value="galaxy" component="a" href="/memory/galaxy" />
        <Tab label="List" value="list" component="a" href="/memory" />
        <Tab label="Health" value="health" component="a" href="/brain/health" />
      </Tabs>
    </Box>
  );
}
