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
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { alpha, useTheme } from "@mui/material/styles";
import BusinessIcon from "@mui/icons-material/Business";
import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PersonIcon from "@mui/icons-material/Person";
import SearchIcon from "@mui/icons-material/Search";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import CompaniesHouseKeyForm from "@/components/companies-house/CompaniesHouseKeyForm";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import {
  fetchCompaniesHouseStatus,
  fetchCompanyProfile,
  fetchOfficerAppointments,
  searchCompaniesHouse,
  type CompanyOfficer,
  type CompanyProfile,
  type CompanySearchHit,
  type OfficerAppointmentCompany,
  type OfficerSearchHit,
} from "@/lib/companies-house-api";
import { importCompaniesHouseLead } from "@/lib/outreach-api";

type SearchMode = "companies" | "officers";

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
  onImport,
  importing,
}: {
  profile: CompanyProfile | null;
  loading: boolean;
  onClose?: () => void;
  onImport?: () => void;
  importing?: boolean;
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
            {profile.has_been_liquidated ? (
              <Chip size="small" color="warning" label="Liquidated" sx={{ height: 22 }} />
            ) : null}
            {profile.has_insolvency_history ? (
              <Chip size="small" color="warning" label="Insolvency history" sx={{ height: 22 }} />
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

      {onImport ? (
        <Button variant="contained" size="small" disabled={importing} onClick={onImport} sx={{ alignSelf: "flex-start" }}>
          {importing ? "Adding lead..." : "Add as lead"}
        </Button>
      ) : null}

      <Box>
        <Typography
          variant="subtitle2"
          sx={{ mb: 1, letterSpacing: 0.4, textTransform: "uppercase", color: "text.secondary" }}
        >
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

function PersonPanel({
  personName,
  companies,
  loading,
  selectedCompanyNumber,
  onSelectCompany,
  onClose,
}: {
  personName: string | null;
  companies: OfficerAppointmentCompany[];
  loading: boolean;
  selectedCompanyNumber: string | null;
  onSelectCompany: (companyNumber: string) => void;
  onClose?: () => void;
}) {
  if (loading) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress size={28} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
          Loading associated companies...
        </Typography>
      </Stack>
    );
  }

  if (!personName) {
    return (
      <EmptyState
        title="No person selected"
        description="Search by person name, then choose a match to see every associated company appointment."
        icon={<PersonIcon sx={{ fontSize: 40 }} />}
      />
    );
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="h6" fontWeight={700}>
            {personName}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {companies.length > 0
              ? `${companies.length} associated compan${companies.length === 1 ? "y" : "ies"}`
              : "No associated companies returned"}
          </Typography>
        </Box>
        {onClose ? (
          <IconButton size="small" onClick={onClose} aria-label="Close person">
            <CloseIcon fontSize="small" />
          </IconButton>
        ) : null}
      </Stack>
      <Divider />
      {companies.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No appointments found for this officer.
        </Typography>
      ) : (
        companies.map((company, idx) => {
          const number = company.company_number || "";
          const active = Boolean(number) && selectedCompanyNumber === number;
          return (
            <ListItemButton
              key={`${number}-${company.officer_role}-${idx}`}
              disabled={!number}
              selected={active}
              onClick={() => number && onSelectCompany(number)}
              sx={{
                borderBottom: "1px solid",
                borderColor: "divider",
                alignItems: "flex-start",
                px: 0.5,
              }}
            >
              <Box sx={{ minWidth: 0, width: "100%" }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
                  <Typography variant="subtitle2" fontWeight={700} noWrap>
                    {company.company_name || number || "Unknown company"}
                  </Typography>
                  <StatusChip status={company.company_status} />
                </Stack>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
                >
                  {number || "No company number"}
                  {company.officer_role ? ` · ${humanizeType(company.officer_role)}` : ""}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {company.appointed_on ? `Appointed ${company.appointed_on}` : ""}
                  {company.resigned_on ? ` · Resigned ${company.resigned_on}` : ""}
                </Typography>
              </Box>
            </ListItemButton>
          );
        })
      )}
    </Stack>
  );
}

export default function CompaniesHouseWorkspace({
  embedded = false,
  workspaceId = "default",
}: {
  embedded?: boolean;
  workspaceId?: string;
}) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const { data: status, error: statusError, mutate: mutateStatus } = useSWR(
    "companies-house-status",
    fetchCompaniesHouseStatus,
  );
  const [mode, setMode] = React.useState<SearchMode>("companies");
  const [query, setQuery] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [companyHits, setCompanyHits] = React.useState<CompanySearchHit[]>([]);
  const [officerHits, setOfficerHits] = React.useState<OfficerSearchHit[]>([]);
  const [total, setTotal] = React.useState<number | null>(null);
  const [selected, setSelected] = React.useState<CompanyProfile | null>(null);
  const [selectedNumber, setSelectedNumber] = React.useState<string | null>(null);
  const [selectedOfficerId, setSelectedOfficerId] = React.useState<string | null>(null);
  const [selectedOfficerName, setSelectedOfficerName] = React.useState<string | null>(null);
  const [appointments, setAppointments] = React.useState<OfficerAppointmentCompany[]>([]);
  const [profileBusy, setProfileBusy] = React.useState(false);
  const [appointmentsBusy, setAppointmentsBusy] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const configured = Boolean(status?.configured && status?.enabled);

  const resetResults = React.useCallback(() => {
    setCompanyHits([]);
    setOfficerHits([]);
    setTotal(null);
    setSelected(null);
    setSelectedNumber(null);
    setSelectedOfficerId(null);
    setSelectedOfficerName(null);
    setAppointments([]);
  }, []);

  const openProfile = React.useCallback(
    async (companyNumber: string) => {
      setSelectedNumber(companyNumber);
      setProfileBusy(true);
      setError(null);
      if (isMobile) setMobileOpen(true);
      try {
        setSelected(await fetchCompanyProfile(companyNumber));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Profile load failed");
      } finally {
        setProfileBusy(false);
      }
    },
    [isMobile],
  );

  const openOfficer = React.useCallback(
    async (hit: OfficerSearchHit) => {
      const officerId = (hit.officer_id || "").trim();
      if (!officerId) {
        setError("This person result is missing an officer id for appointments.");
        return;
      }
      setSelectedOfficerId(officerId);
      setSelectedOfficerName(hit.name || "Officer");
      setSelected(null);
      setSelectedNumber(null);
      setAppointmentsBusy(true);
      setError(null);
      if (isMobile) setMobileOpen(true);
      try {
        const result = await fetchOfficerAppointments(officerId, { max_items: 50 });
        setAppointments(result.companies || []);
        if (result.name) setSelectedOfficerName(result.name);
      } catch (err) {
        setAppointments([]);
        setError(err instanceof Error ? err.message : "Could not load associated companies");
      } finally {
        setAppointmentsBusy(false);
      }
    },
    [isMobile],
  );

  const onSearch = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const q = query.trim();
    if (!q || !configured) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    resetResults();
    try {
      const result = await searchCompaniesHouse(q, { items_per_page: 20, mode });
      setTotal(typeof result.total_results === "number" ? result.total_results : null);
      if (mode === "officers") {
        const items = (result.items || []) as OfficerSearchHit[];
        setOfficerHits(items);
        if (items[0]?.officer_id) await openOfficer(items[0]);
      } else {
        const items = (result.items || []) as CompanySearchHit[];
        setCompanyHits(items);
        if (items[0]?.company_number) await openProfile(items[0].company_number);
      }
    } catch (err) {
      resetResults();
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  };

  const importSelectedLead = async () => {
    if (!selected) return;
    setImporting(true);
    setError(null);
    try {
      await importCompaniesHouseLead(
        {
          company_number: selected.company_number,
          company_name: selected.company_name || selected.company_number,
          company_status: selected.company_status || undefined,
          registered_office: selected.registered_office_address?.formatted || undefined,
          sic_codes: selected.sic_codes,
          officer_names: (selected.officers ?? []).map((o) => o.name).filter(Boolean) as string[],
          tags: ["companies_house"],
        },
        workspaceId,
      );
      setMessage("Company added as outreach lead");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not import company as lead");
    } finally {
      setImporting(false);
    }
  };

  const resultCount = mode === "officers" ? officerHits.length : companyHits.length;
  const resultLabel =
    total != null
      ? `Showing ${resultCount.toLocaleString()} of ${total.toLocaleString()}`
      : resultCount
        ? `${resultCount} result${resultCount === 1 ? "" : "s"}`
        : "Results";

  const statusActions = (
    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
      <Chip
        size="small"
        variant="outlined"
        color={configured ? "success" : "warning"}
        label={configured ? "Live registry" : "Key required"}
      />
      <CompaniesHouseKeyForm status={status} onSaved={async () => { await mutateStatus(); }} />
      {embedded ? (
        <Button component={NextLink} href="/companies-house" size="small" variant="outlined">
          Full browser
        </Button>
      ) : (
        <Button component={NextLink} href="/settings/companies-house" size="small" variant="outlined">
          Settings
        </Button>
      )}
    </Stack>
  );

  const detailLoading = mode === "officers" ? appointmentsBusy || (Boolean(selectedNumber) && profileBusy) : profileBusy;

  return (
    <Box sx={{ maxWidth: 1400, mx: "auto", width: "100%" }}>
      {embedded ? (
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ sm: "center" }}
          spacing={1.5}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="subtitle1" fontWeight={700}>
              Companies House
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Search UK companies or people and see associated appointments.
            </Typography>
          </Box>
          {statusActions}
        </Stack>
      ) : (
        <PageHeader
          title="Companies House"
          description="Search UK companies or people and see associated appointments."
          breadcrumbs={[
            { label: "Research", href: "/research" },
            { label: "Companies House" },
          ]}
          actions={statusActions}
        />
      )}

      {statusError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {statusError instanceof Error ? statusError.message : "Could not load integration status"}
        </Alert>
      ) : null}

      {!configured ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Add a Companies House API key to enable search. Use the key control above, or open Settings.
        </Alert>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
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
        }}
      >
        <ToggleButtonGroup
          exclusive
          size="small"
          value={mode}
          disabled={!configured || busy}
          onChange={(_e, value: SearchMode | null) => {
            if (!value) return;
            setMode(value);
            resetResults();
          }}
          sx={{ mb: 1.5 }}
        >
          <ToggleButton value="companies">
            <BusinessIcon sx={{ fontSize: 16, mr: 0.75 }} />
            Companies
          </ToggleButton>
          <ToggleButton value="officers">
            <PersonIcon sx={{ fontSize: 16, mr: 0.75 }} />
            People
          </ToggleButton>
        </ToggleButtonGroup>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25} alignItems={{ sm: "center" }}>
          <TextField
            inputRef={inputRef}
            fullWidth
            size="medium"
            placeholder={mode === "officers" ? "Person name (e.g. Jane Smith)" : "Company name or number"}
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
            sx={{ "& .MuiOutlinedInput-root": { bgcolor: "background.paper" } }}
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
          sx={{ display: "flex", flexDirection: "column", overflow: "hidden", minHeight: { xs: 320, md: 560 } }}
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

          {mode === "officers" ? (
            !officerHits.length ? (
              <Box sx={{ p: 2, flex: 1 }}>
                <EmptyState
                  title={busy ? "Searching people..." : "Search by person"}
                  description={
                    busy
                      ? "Fetching officer matches from Companies House."
                      : "Find a person, then open associated companies from their appointments."
                  }
                  icon={<PersonIcon sx={{ fontSize: 40 }} />}
                  actionLabel={!busy && configured ? "Focus search" : undefined}
                  onAction={!busy && configured ? () => inputRef.current?.focus() : undefined}
                />
              </Box>
            ) : (
              <List dense disablePadding sx={{ overflow: "auto", flex: 1 }}>
                {officerHits.map((hit, idx) => {
                  const active = selectedOfficerId === hit.officer_id;
                  return (
                    <ListItemButton
                      key={`${hit.officer_id || hit.name}-${idx}`}
                      selected={active}
                      onClick={() => void openOfficer(hit)}
                      sx={{
                        alignItems: "flex-start",
                        py: 1.25,
                        px: 2,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Box sx={{ minWidth: 0, width: "100%" }}>
                        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.5 }}>
                          <Typography variant="subtitle2" fontWeight={700} noWrap>
                            {hit.name || "Unknown person"}
                          </Typography>
                          {typeof hit.appointment_count === "number" ? (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={`${hit.appointment_count} compan${hit.appointment_count === 1 ? "y" : "ies"}`}
                              sx={{ height: 22 }}
                            />
                          ) : null}
                        </Stack>
                        {hit.description ? (
                          <Typography variant="body2" color="text.secondary">
                            {hit.description}
                          </Typography>
                        ) : null}
                        {hit.address_snippet ? (
                          <Typography variant="body2" color="text.secondary" noWrap sx={{ mt: 0.5 }}>
                            {hit.address_snippet}
                          </Typography>
                        ) : null}
                      </Box>
                    </ListItemButton>
                  );
                })}
              </List>
            )
          ) : !companyHits.length ? (
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
              {companyHits.map((hit) => {
                const active = selectedNumber === hit.company_number;
                return (
                  <ListItemButton
                    key={`${hit.company_number}-${hit.title}`}
                    selected={active}
                    onClick={() => void openProfile(hit.company_number)}
                    sx={{
                      alignItems: "flex-start",
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
                        <Typography variant="subtitle2" fontWeight={700} noWrap>
                          {hit.title || hit.company_number}
                        </Typography>
                        <StatusChip status={hit.company_status} />
                      </Stack>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
                      >
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
            {mode === "officers" ? (
              <Stack spacing={2}>
                <PersonPanel
                  personName={selectedOfficerName}
                  companies={appointments}
                  loading={appointmentsBusy}
                  selectedCompanyNumber={selectedNumber}
                  onSelectCompany={(companyNumber) => void openProfile(companyNumber)}
                />
                {selectedNumber || profileBusy ? (
                  <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 2 }}>
                    <ProfilePanel
                      profile={selected}
                      loading={profileBusy}
                      onImport={embedded && selected ? () => void importSelectedLead() : undefined}
                      importing={importing}
                    />
                  </Box>
                ) : null}
              </Stack>
            ) : (
              <ProfilePanel
                profile={selected}
                loading={detailLoading}
                onImport={embedded && selected ? () => void importSelectedLead() : undefined}
                importing={importing}
              />
            )}
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
        {mode === "officers" ? (
          <Stack spacing={2}>
            <PersonPanel
              personName={selectedOfficerName}
              companies={appointments}
              loading={appointmentsBusy}
              selectedCompanyNumber={selectedNumber}
              onSelectCompany={(companyNumber) => void openProfile(companyNumber)}
              onClose={() => setMobileOpen(false)}
            />
            {selectedNumber || profileBusy ? (
              <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 2 }}>
                <ProfilePanel
                  profile={selected}
                  loading={profileBusy}
                  onImport={embedded && selected ? () => void importSelectedLead() : undefined}
                  importing={importing}
                />
              </Box>
            ) : null}
          </Stack>
        ) : (
          <ProfilePanel
            profile={selected}
            loading={profileBusy}
            onClose={() => setMobileOpen(false)}
            onImport={embedded && selected ? () => void importSelectedLead() : undefined}
            importing={importing}
          />
        )}
      </Drawer>
    </Box>
  );
}
