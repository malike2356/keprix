"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { IconCode } from "@tabler/icons-react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock, SkeletonTable } from "@/components/ui/loading";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type SdkManifest = {
  package?: string;
  version?: string;
  modules?: string[];
  endpoints?: Record<string, string>;
  examples?: string[];
};

const MODULE_SNIPPETS: Record<string, string> = {
  agent: `import { Agent, createLocalClient } from "@keprix/sdk";

const client = createLocalClient();
const agent = Agent.define(client, {
  name: "my-agent",
  instructions: "You are helpful.",
});
const result = await agent.run({ message: "Hello" });`,
  workflow: `import { createWorkflow, WorkflowRunner, createLocalClient } from "@keprix/sdk";

const workflow = createWorkflow("demo")
  .task("step1", { key: "ready", value: true })
  .approval("gate", "Continue?")
  .build();
const run = await new WorkflowRunner(createLocalClient()).start(workflow);`,
  evals: `import { defineEvalSuite } from "@keprix/sdk";

const suite = defineEvalSuite("smoke")
  .case({ name: "echo", input: "ping", expect_equals: "ping" });
const report = suite.runLocal((input) => input);`,
};

async function fetchSdkManifest(): Promise<SdkManifest> {
  const response = await ceApi("/api/sdk/typescript/manifest");
  if (!response.ok) {
    throw new Error("Failed to load TypeScript SDK manifest");
  }
  return (await response.json()) as SdkManifest;
}

export default function DeveloperSdkPage() {
  const { data: manifest, error, isLoading } = useSWR("typescript-sdk-manifest", fetchSdkManifest);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <PageHeader
        title="TypeScript SDK"
        description="Agent, workflow, memory, RAG, and eval helpers that call the Keprix backend runtime."
        breadcrumbs={[
          { label: "Developer", href: "/developer" },
          { label: "TypeScript SDK" },
        ]}
      />

      {manifest?.package ? (
        <Stack direction="row" spacing={1} alignItems="center">
          <IconCode size={18} stroke={1.75} />
          <Typography variant="caption" color="text.secondary">
            {manifest.package} v{manifest.version}
          </Typography>
        </Stack>
      ) : null}

      {error ? <Alert severity="error">{error instanceof Error ? error.message : "Failed to load SDK manifest"}</Alert> : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCard title="Modules" subtitle="Exported SDK surface">
            {isLoading ? (
              <SkeletonBlock height={80} />
            ) : (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(manifest?.modules || []).map((module) => (
                  <Chip key={module} label={module} size="small" variant="outlined" />
                ))}
                {!manifest?.modules?.length ? (
                  <Typography variant="body2" color="text.secondary">
                    No modules listed in manifest.
                  </Typography>
                ) : null}
              </Stack>
            )}
          </DashboardCard>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCard title="Examples" subtitle="Reference implementations in the repo">
            {isLoading ? (
              <SkeletonBlock height={80} />
            ) : (
              <Stack spacing={0.5}>
                {(manifest?.examples || ["examples/basic-agent.ts"]).map((example) => (
                  <Typography key={example} variant="body2" sx={{ fontFamily: "monospace" }}>
                    sdk/typescript/{example}
                  </Typography>
                ))}
              </Stack>
            )}
          </DashboardCard>
        </Grid>
      </Grid>

      <DashboardCard title="Backend endpoints" subtitle="Routes the SDK calls on your Keprix instance">
        {isLoading ? (
          <SkeletonTable rows={5} columns={2} />
        ) : !Object.keys(manifest?.endpoints || {}).length ? (
          <Typography variant="body2" color="text.secondary">
            No endpoints listed in manifest.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Key</TableCell>
                <TableCell>Path</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(manifest?.endpoints || {}).map(([key, path]) => (
                <TableRow key={key}>
                  <TableCell>{key}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                      {path}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DashboardCard>

      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        Code samples
      </Typography>

      <Grid container spacing={2}>
        {Object.entries(MODULE_SNIPPETS).map(([name, snippet]) => (
          <Grid key={name} size={{ xs: 12, lg: 4 }}>
            <DashboardCard title={name}>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 2,
                  borderRadius: 1,
                  bgcolor: "background.default",
                  border: 1,
                  borderColor: "divider",
                  fontFamily: "monospace",
                  fontSize: "0.75rem",
                  lineHeight: 1.6,
                  overflow: "auto",
                  whiteSpace: "pre-wrap",
                }}
              >
                {snippet}
              </Box>
            </DashboardCard>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
