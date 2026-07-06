"use client";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import * as React from "react";
import OpenApiExplorer from "@/components/developer/OpenApiExplorer";
import PageHeader from "@/components/ui/PageHeader";
import { getBackendBaseUrl } from "@/lib/ce-api";

export default function ApiDocsPage() {
  const [backendBase, setBackendBase] = React.useState("http://localhost:3333");

  React.useEffect(() => {
    setBackendBase(getBackendBaseUrl());
  }, []);

  const redocUrl = `${backendBase}/redoc`;
  const backendDocsUrl = `${backendBase}/docs`;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)", gap: 2 }}>
      <PageHeader
        title="API documentation"
        description="Interactive OpenAPI explorer for the Keprix backend."
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              component="a"
              href="/openapi.json"
              target="_blank"
              rel="noreferrer"
              size="small"
              variant="outlined"
            >
              OpenAPI JSON
            </Button>
            <Button
              component="a"
              href={backendDocsUrl}
              target="_blank"
              rel="noreferrer"
              size="small"
              variant="outlined"
              endIcon={<OpenInNewIcon fontSize="small" />}
            >
              Backend /docs
            </Button>
            <Button
              component="a"
              href={redocUrl}
              target="_blank"
              rel="noreferrer"
              size="small"
              variant="text"
              endIcon={<OpenInNewIcon fontSize="small" />}
            >
              ReDoc
            </Button>
          </Stack>
        }
      />

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          overflow: "auto",
          bgcolor: "background.paper",
          p: { xs: 1, sm: 2 },
        }}
      >
        <OpenApiExplorer specUrl="/openapi.json" />
      </Box>
    </Box>
  );
}
