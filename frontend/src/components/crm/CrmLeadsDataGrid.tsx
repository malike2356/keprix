"use client";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import dynamic from "next/dynamic";
import * as React from "react";

const CrmLeadsDataGridInner = dynamic(() => import("./CrmLeadsDataGridInner"), {
  ssr: false,
  loading: () => (
    <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
      <CircularProgress size={28} />
    </Box>
  ),
});

/**
 * Client-only shell: MUI DataGrid CSS variables call theme.alpha during SSR
 * and break Next static generation (`t.alpha is not a function`).
 */
export default function CrmLeadsDataGrid() {
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);
  if (!mounted) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress size={28} />
      </Box>
    );
  }
  return <CrmLeadsDataGridInner />;
}
