"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { alpha, useTheme } from "@mui/material/styles";
import BusinessIcon from "@mui/icons-material/Business";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SearchIcon from "@mui/icons-material/Search";
import type { ReactNode } from "react";
import * as React from "react";
import useSWR from "swr";
import CompaniesHouseKeyForm from "@/components/companies-house/CompaniesHouseKeyForm";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchCompaniesHouseStatus,
  fetchCompanyProfile,
  searchCompaniesHouse,
  type CompanyOfficer,
  type CompanyProfile,
  type CompanySearchHit,
} from "@/lib/companies-house-api";

function statusTone(status: string | null | undefined): "success" | "warning" | "default" | "error" {
  const s = (status || "").toLowerCase();
  if (s === "active") return "success";
  if (s.includes("liquidation") || s.includes("receivership") || s.includes("administration")) {
    return "error";
  }
  if (s.includes("dissolved") || s.includes("converted") || s.includes("closed")) return "warning";
  return "default";
}

function humanizeType(value: string | null | undefined): string {
  if (!value) return "";
  return value.replace(/-/g, " ");
}

function StatusChip({ status }: { status?: string | null }) {
  if (!status) return null;
  const tone = statusTone(status);
  return (
    <Chip
      size="small"
      label={status}
      color={tone === "default" ? undefined : tone}
      variant={tone === "default" ? "outlined" : "filled"}
      sx={{ height: 22, fontWeight: 600, textTransform: "lowercase" }}
    />
  );
}

function MetaRow({ label, value }: { label: string; value?: React.ReactNode }) {
  if (value == null || value === "") return null;
  return (
    <Stack direction="row" spacing={2} sx={{ py: 0.75 }}>
      <Typography variant="caption" color="text.secondary" sx={{ width: 120, flexShrink: 0, pt: 0.2 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ flex: 1 }}>
        {value}
      </Typography>
    </Stack>
  );
}

function OfficerRow({ officer }: { officer: CompanyOfficer }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "1.4fr 0.8fr 0.9fr" },
        gap: 0.75,
        py: 1,
        borderBottom: "1px solid",
        borderColor: "divider",
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Typography variant="body2" fontWeight={600}>
        {officer.name || "Unknown"}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ textTransform: "capitalize" }}>
        {officer.officer_role || "-"}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {officer.appointed_on ? `Appointed ${officer.appointed_on}` : ""}
        {officer.resigned_on ? ` · Resigned ${officer.resigned_on}` : ""}
      </Typography>
    </Box>
  );
}

function ProfilePanel({
  profile,
  loading,
  onClose,
}: {
  profile: CompanyProfile | null;
  loading: boolean;
  onClose?: () => void;
}) {
  if (loading) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress size={28} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
          Loading profile...
        </Typography>
      </Stack>
    );
  }

  if (!profile) {
    return (
      <EmptyState
        title="No company selected"
        description="Choose a search result to inspect status, registered office, SIC codes, and officers."
        icon={<BusinessIcon sx={{ fontSize: 40 }} />}
      />
    );
  }

  return (
    <Stack spacing={2.5}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 700, lineHeight: 1.25, mb: 1 }}>
            {profile.company_name || profile.company_number}
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
            <StatusChip status={profile.company_status} />
            {profile.type ? (
              <Chip size="small" variant="outlined" label={humanizeType(profile.type)} sx={{ height: 22 }} />
            ) : null}
            {profile.has_insolvency_history ? (
              <Chip size="small" color="warning" label="Insolvency history" sx={{ height: 22 }} />
            ) : null}
            {profile.has_charges ? (
              <Chip size="small" variant="outlined" label="Charges" sx={{ height: 22 }} />
            ) : null}
          </Stack>
        </Box>
        {onClose ? (
          <IconButton size="small" onClick={onClose} aria-label="Close profile">
            <CloseIcon fontSize="small" />
          </IconButton>
        ) : null}
      </Stack>

      <Paper variant="outlined" sx={{ p: 1.5, bgcolor: "transparent" }}>
        <MetaRow label="Number" value={profile.company_number} />
        <MetaRow label="Incorporated" value={profile.date_of_creation} />
        <MetaRow label="Jurisdiction" value={profile.jurisdiction} />
        <MetaRow label="Office" value={profile.registered_office_address?.formatted} />
        <MetaRow
          label="SIC"
          value={
            profile.sic_codes && profile.sic_codes.length > 0 ? (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                {profile.sic_codes.map((code) => (
                  <Chip key={code} size="small" label={code} variant="outlined" sx={{ height: 22 }} />
                ))}
              </Stack>
            ) : null
          }
        />
      </Paper>

      {profile.public_url ? (
        <Button
          component={Link}
          href={profile.public_url}
          target="_blank"
          rel="noreferrer"
          variant="outlined"
          endIcon={<OpenInNewIcon />}
          sx={{ alignSelf: "flex-start" }}
        >
          Open on Companies House
        </Button>
      ) : null}

      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1, letterSpacing: 0.4, textTransform: "uppercase", color: "text.secondary" }}>
          Officers
        </Typography>
        <Divider sx={{ mb: 0.5 }} />
        {(profile.officers || []).length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 1.5 }}>
            No officers returned for this company.
          </Typography>
        ) : (
          (profile.officers || []).slice(0, 20).map((officer, idx) => (
            <OfficerRow key={`${officer.name}-${idx}`} officer={officer} />
          ))
        )}
      </Box>
    </Stack>
  );
}

export default function CompaniesHousePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const { data: status, error: statusError, mutate: mutateStatus } = useSWR(
    "companies-house-status",
    fetchCompaniesHouseStatus,
  );
  const [query, setQuery] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [hits, setHits] = React.useState<CompanySearchHit[]>([]);
  const [total, setTotal] = React.useState<number | null>(null);
  const [selected, setSelected] = React.useState<CompanyProfile | null>(null);
  const [selectedNumber, setSelectedNumber] = React.useState<string | null>(null);
  const [profileBusy, setProfileBusy] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const configured = Boolean(status?.configured && status?.enabled);

  const openProfile = React.useCallback(async (companyNumber: string) => {
    setSelectedNumber(companyNumber);
    setProfileBusy(true);
    setError(null);
    if (isMobile) setMobileOpen(true);
    try {
      const profile = await fetchCompanyProfile(companyNumber);
      setSelected(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Profile load failed");
    } finally {
      setProfileBusy(false);
    }
  }, [isMobile]);

  const onSearch = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const q = query.trim();
    if (!q || !configured) return;
    setBusy(true);
    setError(null);
    setSelected(null);
    setSelectedNumber(null);
    try {
      const result = await searchCompaniesHouse(q, { items_per_page: 20 });
      const items = result.items || [];
      setHits(items);
      setTotal(typeof result.total_results === "number" ? result.total_results : null);
      if (items[0]?.company_number) {
        await openProfile(items[0].company_number);
      }
    } catch (err) {
      setHits([]);
      setTotal(null);
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  };

  const resultLabel =
    total != null
      ? `Showing ${hits.length.toLocaleString()} of ${total.toLocaleString()}`
      : hits.length
        ? `${hits.length} result${hits.length === 1 ? "" : "s"}`
        : "Results";

  return (
    <Box sx={{ maxWidth: 1400, mx: "auto" }}>
      <PageHeader
        title="Companies House"
        description="UK public registry search and company profiles."
        breadcrumbs={[
          { label: "Research", href: "/research" },
          { label: "Companies House" },
        ]}
        actions={
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              variant="outlined"
              color={configured ? "success" : "warning"}
              label={configured ? "Live registry" : "Key required"}
            />
            <CompaniesHouseKeyForm status={status} onSaved={() => mutateStatus()} />
          </Stack>
        }
      />

      {statusError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {statusError instanceof Error ? statusError.message : "Could not load integration status"}
        </Alert>
      ) : null}

      {!configured ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Add a Companies House API key to enable search. Use the key icon above, or open Settings.
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Paper
        component="form"
        onSubmit={onSearch}
        elevation={0}
        variant="outlined"
        sx={{
          p: { xs: 1.5, sm: 2 },
          mb: 2.5,
          bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === "dark" ? 0.06 : 0.03),
          borderColor: alpha(theme.palette.divider, 0.9),
        }}
      >
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ sm: "center" }}>
          <TextField
            inputRef={inputRef}
            fullWidth
            size="medium"
            placeholder="Company name or number"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={!configured || busy}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
            sx={{
              "& .MuiOutlinedInput-root": {
                bgcolor: "background.paper",
              },
            }}
          />
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={!configured || busy || !query.trim()}
            sx={{ minWidth: 128, height: 56 }}
          >
            {busy ? <CircularProgress size={20} color="inherit" /> : "Search"}
          </Button>
        </Stack>
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1.05fr) minmax(0, 0.95fr)" },
          gap: 2,
          alignItems: "stretch",
          minHeight: { md: 560 },
        }}
      >
        <Paper
          variant="outlined"
          sx={{
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            minHeight: { xs: 320, md: 560 },
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ px: 2, py: 1.25, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Typography variant="subtitle2" sx={{ letterSpacing: 0.3 }}>
              {resultLabel}
            </Typography>
            {busy ? <CircularProgress size={16} /> : null}
          </Stack>

          {!hits.length ? (
            <Box sx={{ p: 2, flex: 1 }}>
              <EmptyState
                title={busy ? "Searching registry..." : "Start a search"}
                description={
                  busy
                    ? "Fetching matches from Companies House."
                    : "Try a trading name, registered name, or company number."
                }
                icon={<SearchIcon sx={{ fontSize: 40 }} />}
                actionLabel={!busy && configured ? "Focus search" : undefined}
                onAction={!busy && configured ? () => inputRef.current?.focus() : undefined}
              />
            </Box>
          ) : (
            <List dense disablePadding sx={{ overflow: "auto", flex: 1 }}>
              {hits.map((hit) => {
                const active = selectedNumber === hit.company_number;
                return (
                  <ListItemButton
                    key={`${hit.company_number}-${hit.title}`}
                    selected={active}
                    onClick={() => openProfile(hit.company_number)}
                    sx={{
                      alignItems: "flex-start",
                      gap: 1,
                      py: 1.25,
                      px: 2,
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      "&.Mui-selected": {
                        bgcolor: alpha(theme.palette.primary.main, theme.palette.mode === "dark" ? 0.16 : 0.08),
                      },
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
                          {hit.title || hit.company_number}
                        </Typography>
                        <StatusChip status={hit.company_status} />
                      </Stack>
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
                        {hit.company_number}
                        {hit.company_type ? ` · ${humanizeType(hit.company_type)}` : ""}
                        {hit.date_of_creation ? ` · ${hit.date_of_creation}` : ""}
                      </Typography>
                      {hit.address_snippet ? (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }} noWrap>
                          {hit.address_snippet}
                        </Typography>
                      ) : null}
                    </Box>
                  </ListItemButton>
                );
              })}
            </List>
          )}
        </Paper>

        {!isMobile ? (
          <Paper variant="outlined" sx={{ p: 2.5, minHeight: 560, overflow: "auto" }}>
            <ProfilePanel profile={selected} loading={profileBusy} />
          </Paper>
        ) : null}
      </Box>

      <Drawer
        anchor="bottom"
        open={isMobile && mobileOpen}
        onClose={() => setMobileOpen(false)}
        PaperProps={{
          sx: {
            height: "86vh",
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
            p: 2,
          },
        }}
      >
        <ProfilePanel profile={selected} loading={profileBusy} onClose={() => setMobileOpen(false)} />
      </Drawer>
    </Box>
  );
}
