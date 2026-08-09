"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  type FeatureFlag,
  fetchFeatureFlags,
  resetAllFeatureFlags,
  resetFeatureFlag,
  setFeatureFlag,
} from "@/lib/feature-flag-api";

const VIEW_STORAGE_KEY = "keprix.admin.featureFlags.view";

type ViewMode = "grid" | "list";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

function readStoredView(): ViewMode {
  if (typeof window === "undefined") return "grid";
  const raw = window.localStorage.getItem(VIEW_STORAGE_KEY);
  return raw === "list" ? "list" : "grid";
}

function FlagStateChips({ flag }: { flag: FeatureFlag }) {
  return (
    <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
      <Chip
        size="small"
        label={flag.effective_value ? "On" : "Off"}
        color={flag.effective_value ? "success" : "default"}
        variant={flag.effective_value ? "filled" : "outlined"}
      />
      {flag.overridden ? <Chip size="small" label="Override" color="warning" variant="outlined" /> : null}
      {!flag.overridden && flag.runtime_value !== flag.default ? (
        <Chip size="small" label="Runtime default" variant="outlined" />
      ) : null}
      {flag.tags?.map((tag) => (
        <Chip key={tag} size="small" label={tag} variant="outlined" />
      ))}
    </Stack>
  );
}

function FlagCard({
  flag,
  busyId,
  onToggle,
  onReset,
}: {
  flag: FeatureFlag;
  busyId: string | null;
  onToggle: (flag: FeatureFlag, enabled: boolean) => void;
  onReset: (flag: FeatureFlag) => void;
}) {
  const busy = busyId === flag.id;
  return (
    <Paper variant="outlined" sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column", gap: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle1" component="h2">
            {flag.name}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
            {flag.id}
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={flag.effective_value}
              disabled={busy}
              onChange={(_, checked) => onToggle(flag, checked)}
              inputProps={{ "aria-label": `Toggle ${flag.name}` }}
            />
          }
          label=""
          sx={{ m: 0 }}
        />
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
        {flag.description}
      </Typography>
      <FlagStateChips flag={flag} />
      <Typography variant="caption" color="text.secondary">
        Category: {flag.category} · catalog default {flag.default ? "on" : "off"} · runtime{" "}
        {flag.runtime_value ? "on" : "off"}
      </Typography>
      <Box>
        <Button size="small" disabled={!flag.overridden || busy} onClick={() => onReset(flag)}>
          Reset to runtime default
        </Button>
      </Box>
    </Paper>
  );
}

export default function AdminFeatureFlagsPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const { data, error, isLoading, mutate } = useSWR(
    isAdmin ? "admin-feature-flags" : null,
    fetchFeatureFlags,
    { refreshInterval: 30_000 },
  );

  const [view, setView] = React.useState<ViewMode>("grid");
  const [category, setCategory] = React.useState<string>("all");
  const [query, setQuery] = React.useState("");
  const [busyId, setBusyId] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [confirmResetAll, setConfirmResetAll] = React.useState(false);
  const [resettingAll, setResettingAll] = React.useState(false);

  React.useEffect(() => {
    setView(readStoredView());
  }, []);

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(VIEW_STORAGE_KEY, view);
    }
  }, [view]);

  const flags = data?.flags ?? [];
  const categories = data?.categories ?? [];

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return flags.filter((flag) => {
      if (category !== "all" && flag.category !== category) return false;
      if (!q) return true;
      return (
        flag.id.toLowerCase().includes(q) ||
        flag.name.toLowerCase().includes(q) ||
        flag.description.toLowerCase().includes(q) ||
        flag.tags.some((t) => t.toLowerCase().includes(q))
      );
    });
  }, [flags, category, query]);

  async function onToggle(flag: FeatureFlag, enabled: boolean) {
    setBusyId(flag.id);
    setActionError(null);
    try {
      await setFeatureFlag(flag.id, enabled);
      setMessage(`${flag.name} set to ${enabled ? "on" : "off"}. Takes effect on the next UI contract refresh.`);
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update flag");
    } finally {
      setBusyId(null);
    }
  }

  async function onReset(flag: FeatureFlag) {
    setBusyId(flag.id);
    setActionError(null);
    try {
      await resetFeatureFlag(flag.id);
      setMessage(`Cleared override for ${flag.name}.`);
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to reset flag");
    } finally {
      setBusyId(null);
    }
  }

  async function onResetAll() {
    setResettingAll(true);
    setActionError(null);
    try {
      await resetAllFeatureFlags();
      setConfirmResetAll(false);
      setMessage("All feature flag overrides cleared.");
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to reset all flags");
    } finally {
      setResettingAll(false);
    }
  }

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Feature flags" description="Runtime feature flag overrides." />
        <SkeletonList rows={4} rowHeight={56} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader
          title="Feature flags"
          description="Runtime feature flag overrides for progressive UI surfaces."
          breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Feature flags" }]}
        />
        <Alert severity="error">
          Admin role required. Your role ({user?.role || "unknown"}) cannot manage feature flags.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Feature flags"
        description="Progressive UI surface toggles for users and operators. Admins always keep full navigation. Wider module catalog lives under Settings → Modules."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Feature flags" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/settings/modules" variant="outlined" size="small">
              Modules
            </Button>
            <Button
              color="warning"
              variant="outlined"
              size="small"
              disabled={!data?.override_count}
              onClick={() => setConfirmResetAll(true)}
            >
              Reset all overrides
            </Button>
          </Stack>
        }
      />

      {(error || actionError) && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={actionError ? () => setActionError(null) : undefined}
        >
          {actionError || (error instanceof Error ? error.message : "Failed to load feature flags")}
        </Alert>
      )}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Alert severity="info" sx={{ mb: 2 }}>
        Overrides persist immediately and apply on the next UI contract request (no restart). They do
        not hide Admin nav for owners. Flags are progressive surfaces, not a full backend module map.
      </Alert>

      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        alignItems={{ md: "center" }}
        sx={{ mb: 2 }}
      >
        <Chip size="small" label={`${flags.length} flags`} />
        <Chip
          size="small"
          color={data?.override_count ? "warning" : "default"}
          label={`${data?.override_count ?? 0} overrides`}
          variant="outlined"
        />
        <TextField
          size="small"
          label="Search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="ff-category">Category</InputLabel>
          <Select
            labelId="ff-category"
            label="Category"
            value={category}
            onChange={(e) => setCategory(String(e.target.value))}
          >
            <MenuItem value="all">All categories</MenuItem>
            {categories.map((c) => (
              <MenuItem key={c} value={c}>
                {c}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_, next: ViewMode | null) => {
            if (next) setView(next);
          }}
          aria-label="Feature flag view mode"
        >
          <ToggleButton value="grid">Grid</ToggleButton>
          <ToggleButton value="list">List</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {isLoading ? (
        view === "list" ? (
          <SkeletonTable rows={8} columns={5} />
        ) : (
          <SkeletonList rows={6} rowHeight={120} />
        )
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No matching flags"
          description="Try another category or clear the search. Known progressive surfaces are registered in the feature flag catalog."
        />
      ) : view === "grid" ? (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              lg: "repeat(3, minmax(0, 1fr))",
            },
          }}
        >
          {filtered.map((flag) => (
            <FlagCard
              key={flag.id}
              flag={flag}
              busyId={busyId}
              onToggle={onToggle}
              onReset={onReset}
            />
          ))}
        </Box>
      ) : (
        <Paper variant="outlined" sx={{ overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Flag</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>State</TableCell>
                <TableCell align="center">Enabled</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((flag) => (
                <TableRow key={flag.id} hover>
                  <TableCell>
                    <Typography variant="subtitle2">{flag.name}</Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {flag.id}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 420 }}>
                      {flag.description}
                    </Typography>
                  </TableCell>
                  <TableCell>{flag.category}</TableCell>
                  <TableCell>
                    <FlagStateChips flag={flag} />
                  </TableCell>
                  <TableCell align="center">
                    <Switch
                      checked={flag.effective_value}
                      disabled={busyId === flag.id}
                      onChange={(_, checked) => onToggle(flag, checked)}
                      inputProps={{ "aria-label": `Toggle ${flag.name}` }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      disabled={!flag.overridden || busyId === flag.id}
                      onClick={() => onReset(flag)}
                    >
                      Reset
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      <Dialog open={confirmResetAll} onClose={() => (!resettingAll ? setConfirmResetAll(false) : undefined)}>
        <DialogTitle>Reset all overrides?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This clears every stored override and restores runtime defaults for all flags. Catalog
            defaults and live runtime values remain; only admin overrides in{" "}
            <code>feature_flags.json</code> are removed.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmResetAll(false)} disabled={resettingAll}>
            Cancel
          </Button>
          <Button color="warning" variant="contained" onClick={onResetAll} disabled={resettingAll}>
            {resettingAll ? "Resetting…" : "Reset all"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
