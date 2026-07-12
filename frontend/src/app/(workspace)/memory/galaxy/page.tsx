"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import BrainSectionTabs from "@/components/memory/BrainSectionTabs";
import MemoryGalaxyCanvas, {
  type GalaxyLayoutMode,
  type VaultGraphPayload,
} from "@/components/memory/MemoryGalaxyCanvas";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonBlock } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";

async function fetchVaultGraph(): Promise<VaultGraphPayload> {
  const response = await ceApi("/api/vault/graph");
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Failed to load vault graph");
  }
  return (await response.json()) as VaultGraphPayload;
}

export default function MemoryGalaxyPage() {
  const { data, error, isLoading, mutate } = useSWR("vault-memory-galaxy", fetchVaultGraph);
  const [layoutMode, setLayoutMode] = React.useState<GalaxyLayoutMode>("circle");

  return (
    <Box>
      <PageHeader
        title="Memory Galaxy"
        description="Shape of what you know: wiki-links across the single markdown vault. Click a node to open the note."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Brain", href: "/memory" },
          { label: "Galaxy" },
        ]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component={Link} href="/settings/vault" variant="outlined" size="small">
              Vault settings
            </Button>
            <Button component={Link} href="/agent-os/glass" variant="outlined" size="small">
              Agent OS glass
            </Button>
            <Button onClick={() => mutate()} size="small">
              Refresh
            </Button>
          </Stack>
        }
      />
      <BrainSectionTabs value="galaxy" />
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Chip label={`${data?.nodes?.length ?? 0} notes`} size="small" />
        <Chip label={`${data?.edges?.length ?? 0} links`} size="small" />
        <Chip label="One vault" size="small" variant="outlined" />
      </Stack>
      {error ? (
        <ErrorState title="Galaxy failed to load" message={error.message} onRetry={() => void mutate()} />
      ) : null}
      {isLoading && !data ? <SkeletonBlock height={480} /> : null}
      {!error ? (
        <MemoryGalaxyCanvas
          graph={data}
          loading={isLoading && !data}
          layoutMode={layoutMode}
          onLayoutModeChange={setLayoutMode}
        />
      ) : null}
    </Box>
  );
}
