"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import DocumentVaultExplorer from "@/components/document-vault/DocumentVaultExplorer";
import FileBrowserPage from "@/components/files/FileBrowserPage";
import { useCESession } from "@/lib/ce-auth";

function FilesPageInner() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");
  const { user } = useCESession();
  const isAdmin =
    user?.role === "admin" || user?.role === "owner" || user?.role === "developer";

  if (mode === "host") {
    return (
      <Box>
        <Alert severity="info" sx={{ mb: 2 }}>
          Admin host filesystem mode. This is not the tenant Document Vault.
          {" "}
          <Button size="small" href="/files" component="a">
            Back to Document Vault
          </Button>
        </Alert>
        <FileBrowserPage />
      </Box>
    );
  }

  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Tenant Document Vault (default for /files). Host machine paths stay admin-only.
        </Typography>
        {isAdmin ? (
          <Button size="small" variant="outlined" href="/files?mode=host" component="a">
            Open host FS
          </Button>
        ) : null}
      </Stack>
      <DocumentVaultExplorer showHostFsLink={isAdmin} />
    </Box>
  );
}

export default function FilesPage() {
  return (
    <React.Suspense fallback={<Typography sx={{ p: 2 }}>Loading Document Vault...</Typography>}>
      <FilesPageInner />
    </React.Suspense>
  );
}
