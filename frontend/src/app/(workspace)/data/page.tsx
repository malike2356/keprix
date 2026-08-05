"use client";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import * as React from "react";
import DataWorkspaceClient from "./DataWorkspaceClient";

export default function DataWorkspacePage() {
  return (
    <React.Suspense
      fallback={
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress size={28} />
        </Box>
      }
    >
      <DataWorkspaceClient />
    </React.Suspense>
  );
}
