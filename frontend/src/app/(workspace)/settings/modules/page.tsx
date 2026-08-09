"use client";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SearchIcon from "@mui/icons-material/Search";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import {
  fetchModulesCatalog,
  formatModuleCategory,
  formatModuleStatus,
  moduleStatusColor,
  type GuiModule,
  type GuiModuleStatus,
} from "@/lib/modules-api";

type StatusFilter = "all" | "available" | "partial" | "cli_api";

function matchesQuery(module: GuiModule, query: string): boolean {
  if (!query) return true;
  const haystack = [module.name, module.description, module.id, module.module, module.category]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function groupByCategory(modules: GuiModule[]): Array<[string, GuiModule[]]> {
  const groups = new Map<string, GuiModule[]>();
  for (const module of modules) {
    const key = module.category || "other";
    const list = groups.get(key) || [];
    list.push(module);
    groups.set(key, list);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export default function SettingsModulesPage() {
  const { data, error, isLoading, mutate } = useSWR("settings-modules-catalog", fetchModulesCatalog, {
    revalidateOnFocus: false,
  });
  const [query, setQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("all");

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.modules || []).filter((module) => {
      if (statusFilter !== "all" && module.gui_status !== statusFilter) return false;
      return matchesQuery(module, q);
    });
  }, [data?.modules, query, statusFilter]);

  const grouped = React.useMemo(() => groupByCategory(filtered), [filtered]);

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Modules"
        description="Catalog of Keprix packages and surfaces beyond the curated sidebar. Open available GUIs, or use CLI/API where noted."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Modules" }]}
      />

      {error ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void mutate()}>
              Retry
            </Button>
          }
        >
          {error instanceof Error ? error.message : "Failed to load modules catalog"}
        </Alert>
      ) : null}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }} flexWrap="wrap">
        <Chip label={`Installed ${data?.installed_version ?? "-"}`} />
        <Chip color="success" label={`Available ${data?.counts.available ?? "-"}`} />
        <Chip color="warning" label={`Partial ${data?.counts.partial ?? "-"}`} />
        <Chip label={`CLI / API ${data?.counts.cli_api ?? "-"}`} />
        <Chip variant="outlined" label={`Total ${data?.counts.total ?? "-"}`} />
        <Box sx={{ flex: 1 }} />
        <Button component="a" href="/developer/module-inventory" size="small" variant="text">
          Developer inventory
        </Button>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
        <TextField
          size="small"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search modules"
          sx={{ minWidth: { md: 280 }, flex: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <ToggleButtonGroup
          exclusive
          size="small"
          value={statusFilter}
          onChange={(_event, value: StatusFilter | null) => {
            if (value) setStatusFilter(value);
          }}
        >
          <ToggleButton value="all">All</ToggleButton>
          <ToggleButton value="available">Available</ToggleButton>
          <ToggleButton value="partial">Partial</ToggleButton>
          <ToggleButton value="cli_api">CLI / API</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {isLoading && !data ? <SkeletonList rows={6} /> : null}

      {!isLoading && data && filtered.length === 0 ? (
        <Alert severity="info">No modules match this search or filter.</Alert>
      ) : null}

      {grouped.map(([category, modules]) => (
        <DashboardCard
          key={category}
          title={formatModuleCategory(category)}
          subtitle={`${modules.length} module${modules.length === 1 ? "" : "s"}`}
        >
          <Box sx={{ display: "grid", gap: 1.5 }}>
            {modules.map((module) => (
              <ModuleRow key={module.id} module={module} />
            ))}
          </Box>
        </DashboardCard>
      ))}

      <Typography variant="body2" color="text.secondary">
        Feature flags control progressive UI disclosure separately under Admin. Module statuses come
        from the upgrade GUI catalog (`available`, `partial`, `cli_api`).
      </Typography>
    </Box>
  );
}

function ModuleRow({ module }: { module: GuiModule }) {
  const status = module.gui_status as GuiModuleStatus;
  const href = module.gui_href;

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1fr auto" },
        gap: 1.5,
        alignItems: "center",
        py: 1.25,
        borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
        "&:last-of-type": { borderBottom: "none", pb: 0 },
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {module.name}
          </Typography>
          <Chip size="small" color={moduleStatusColor(status)} label={formatModuleStatus(status)} />
          <Chip size="small" variant="outlined" label={`v${module.version}`} />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {module.description}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace", display: "block", mt: 0.5 }}>
          {module.module}
          {href ? ` · ${href}` : ""}
        </Typography>
      </Box>
      <Box sx={{ display: "flex", gap: 1, justifyContent: { xs: "stretch", md: "flex-end" } }}>
        {href ? (
          <Button
            component="a"
            href={href}
            variant={status === "available" ? "contained" : "outlined"}
            size="small"
            endIcon={<OpenInNewIcon fontSize="small" />}
          >
            Open
          </Button>
        ) : (
          <Chip size="small" label="No GUI route" variant="outlined" />
        )}
      </Box>
    </Box>
  );
}
