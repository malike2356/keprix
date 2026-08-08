"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import { fetchPersonaSkillPacks, fetchPersonasInventory } from "@/lib/platform-admin-api";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

type PersonaRow = {
  name?: string;
  role?: string;
  tone?: string;
  agent_type?: string;
  description?: string;
  [key: string]: unknown;
};

export default function PersonasInventoryPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [workspaceId, setWorkspaceId] = React.useState("default");
  const [query, setQuery] = React.useState("");
  const [selectedName, setSelectedName] = React.useState<string | null>(null);

  const personas = useSWR(isAdmin ? ["personas-inventory", workspaceId] : null, () =>
    fetchPersonasInventory(workspaceId),
  );
  const packs = useSWR(
    isAdmin && selectedName ? ["persona-packs", selectedName] : null,
    () => fetchPersonaSkillPacks(selectedName!),
  );

  const rows = React.useMemo(() => {
    const list = (personas.data?.personas ?? []) as PersonaRow[];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((row) => {
      const hay = `${row.name || ""} ${row.role || ""} ${row.tone || ""} ${row.agent_type || ""} ${row.description || ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [personas.data, query]);

  const selected = rows.find((row) => String(row.name || "") === selectedName) || null;

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Personas" description="Registered personas and skill packs." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Personas"
          description="Operator inventory of registered personas and skill packs."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Personas" }]}
        />
        <Alert severity="error">Admin role required to browse the persona inventory.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Personas"
        description="Operator inventory of registered personas and attached skill packs for this workspace."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Personas" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component={NextLink} href="/admin/typed-agents" size="small" variant="outlined">
              Typed agents
            </Button>
            <Button component={NextLink} href="/settings/modules" size="small" variant="outlined">
              Modules
            </Button>
          </Stack>
        }
      />

      {personas.error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {personas.error.message}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }} alignItems={{ md: "center" }}>
        <TextField
          size="small"
          label="Workspace id"
          value={workspaceId}
          onChange={(e) => setWorkspaceId(e.target.value)}
        />
        <TextField
          size="small"
          label="Search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ minWidth: 240 }}
        />
        <Chip size="small" label={`${rows.length} personas`} variant="outlined" />
        <Button size="small" onClick={() => void personas.mutate()}>
          Refresh
        </Button>
      </Stack>

      {personas.isLoading ? (
        <SkeletonTable rows={6} columns={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No personas"
          description="The persona registry returned empty for this workspace. Seed or install persona packs, then refresh."
        />
      ) : (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.2fr) minmax(280px, 0.8fr)" },
          }}
        >
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Tone</TableCell>
                  <TableCell>Type</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => {
                  const n = String(row.name || "");
                  return (
                    <TableRow
                      key={n}
                      hover
                      selected={selectedName === n}
                      onClick={() => setSelectedName(n)}
                      sx={{ cursor: "pointer" }}
                    >
                      <TableCell>{n || ";"}</TableCell>
                      <TableCell>{String(row.role || ";")}</TableCell>
                      <TableCell>{String(row.tone || ";")}</TableCell>
                      <TableCell>{String(row.agent_type || ";")}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            {!selectedName ? (
              <Typography variant="body2" color="text.secondary">
                Select a persona to inspect metadata and skill packs.
              </Typography>
            ) : (
              <Stack spacing={1.5}>
                <Typography variant="h6" component="h2">
                  {selectedName}
                </Typography>
                {selected?.description ? (
                  <Typography variant="body2" color="text.secondary">
                    {String(selected.description)}
                  </Typography>
                ) : null}
                <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                  {selected?.role ? <Chip size="small" label={`role: ${String(selected.role)}`} /> : null}
                  {selected?.tone ? <Chip size="small" label={`tone: ${String(selected.tone)}`} variant="outlined" /> : null}
                  {selected?.agent_type ? (
                    <Chip size="small" label={`type: ${String(selected.agent_type)}`} variant="outlined" />
                  ) : null}
                </Stack>
                <Typography variant="subtitle2">Skill packs</Typography>
                {packs.error ? (
                  <Alert severity="warning">{packs.error.message}</Alert>
                ) : packs.isLoading ? (
                  <SkeletonList rows={3} rowHeight={36} />
                ) : (
                  <StructuredDataView value={packs.data || {}} emptyLabel="No skill packs returned" />
                )}
                <Typography variant="subtitle2">Raw persona record</Typography>
                <StructuredDataView value={selected || {}} emptyLabel="No metadata" />
              </Stack>
            )}
          </Paper>
        </Box>
      )}
    </Box>
  );
}
