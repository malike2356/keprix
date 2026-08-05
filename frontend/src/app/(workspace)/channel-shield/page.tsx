"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createProtection,
  destroyMessage,
  fetchAdapterHealth,
  fetchAgentOsPanel,
  fetchEmployeeAction,
  fetchMessage,
  fetchMessages,
  fetchProtections,
  fetchSettings,
  releaseMessage,
  requestApproval,
  type AgentOsPanel,
  type EmployeeAction,
  type ShieldMessage,
  type ShieldProtection,
} from "@/lib/channel-shield-api";

const CHANNELS = [
  "email",
  "slack",
  "teams",
  "telegram",
  "whatsapp",
  "discord",
  "sms",
  "web",
] as const;

/** Page-local palette: shell theme tokens can become unreadable on this security surface. */
const C = {
  page: "#f8fafc",
  panel: "#ffffff",
  panelAlt: "#f1f5f9",
  panelBorder: "#cbd5e1",
  strongBorder: "#334155",
  text: "#0f172a",
  muted: "#475569",
  subtle: "#64748b",
  soft: "#eef2f7",
  softBorder: "#cbd5e1",
  selected: "#dbeafe",
  selectedBorder: "#2563eb",
  primary: "#1d4ed8",
  primaryText: "#ffffff",
  danger: "#b91c1c",
  dangerSoft: "#fef2f2",
  warningText: "#7c2d12",
  warningSoft: "#fff7ed",
  warningBorder: "#fdba74",
  infoText: "#0f3b63",
  infoSoft: "#eff6ff",
  infoBorder: "#93c5fd",
};

const buttonOutlineSx = {
  borderColor: C.strongBorder,
  color: C.text,
  fontWeight: 800,
  "&:hover": {
    borderColor: C.primary,
    bgcolor: C.selected,
  },
};

const textFieldSx = {
  "& .MuiInputBase-root": {
    bgcolor: C.panel,
    color: C.text,
  },
  "& .MuiInputLabel-root": {
    color: C.muted,
    fontWeight: 700,
  },
  "& .MuiInputLabel-root.Mui-focused": {
    color: C.primary,
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: C.softBorder,
  },
  "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: C.strongBorder,
  },
  "& .MuiFormHelperText-root": {
    color: C.muted,
  },
};

function chipSx(active = false) {
  return {
    fontWeight: 800,
    color: active ? C.primaryText : C.text,
    bgcolor: active ? C.primary : C.panel,
    border: `1px solid ${active ? C.primary : C.softBorder}`,
    "& .MuiChip-label": { color: "inherit", px: 1.25 },
    "&:hover": { bgcolor: active ? "#1e40af" : C.panelAlt },
  };
}

function alertSx(kind: "warning" | "info" | "error") {
  if (kind === "error") {
    return {
      mb: 2,
      color: C.danger,
      bgcolor: C.dangerSoft,
      border: `1px solid ${C.danger}`,
      "& .MuiAlert-icon": { color: C.danger },
    };
  }
  if (kind === "info") {
    return {
      mb: 2,
      whiteSpace: "pre-wrap",
      color: C.infoText,
      bgcolor: C.infoSoft,
      border: `1px solid ${C.infoBorder}`,
      "& .MuiAlert-icon": { color: C.primary },
    };
  }
  return {
    mb: 2,
    whiteSpace: "pre-wrap",
    color: C.warningText,
    bgcolor: C.warningSoft,
    border: `1px solid ${C.warningBorder}`,
    "& .MuiAlert-icon": { color: "#c2410c" },
  };
}

function verdictColor(verdict: string | null): "default" | "success" | "warning" | "error" {
  if (verdict === "clean") return "success";
  if (verdict === "suspect") return "warning";
  if (verdict === "malicious" || verdict === "error") return "error";
  return "default";
}

function FilterChip({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <Chip
      label={label}
      clickable
      disabled={disabled}
      onClick={onClick}
      sx={chipSx(active)}
    />
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box
      sx={{
        border: `1px solid ${C.panelBorder}`,
        borderRadius: 1,
        bgcolor: C.panel,
        color: C.text,
        p: 2,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
      }}
    >
      <Typography sx={{ mb: 1.5, fontWeight: 800, fontSize: "1.05rem", color: C.text }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 1,
        bgcolor: C.panelAlt,
        border: `1px solid ${C.softBorder}`,
      }}
    >
      <Typography sx={{ fontWeight: 800, color: C.text, mb: 0.5 }}>{title}</Typography>
      <Typography sx={{ color: C.muted, fontSize: "0.95rem", lineHeight: 1.4 }}>{body}</Typography>
    </Box>
  );
}

function LoadingRows({ rows = 4, height = 72 }: { rows?: number; height?: number }) {
  return (
    <Stack spacing={1.5} aria-label="Loading">
      {Array.from({ length: rows }).map((_, index) => (
        <Box
          key={index}
          sx={{
            height,
            borderRadius: 1,
            border: `1px solid ${C.panelBorder}`,
            bgcolor: C.panelAlt,
            backgroundImage:
              "linear-gradient(90deg, rgba(203, 213, 225, 0.72), rgba(241, 245, 249, 0.95), rgba(203, 213, 225, 0.72))",
            backgroundSize: "220% 100%",
          }}
        />
      ))}
    </Stack>
  );
}

function LoadingDetail() {
  return (
    <Stack spacing={1.5} aria-label="Loading detail">
      <Box sx={{ width: "54%", height: 22, borderRadius: 1, bgcolor: "#cbd5e1" }} />
      <Box sx={{ width: "38%", height: 16, borderRadius: 1, bgcolor: "#d6dee9" }} />
      <Divider />
      <LoadingRows rows={4} height={44} />
      <Box sx={{ display: "flex", gap: 1 }}>
        <Box sx={{ width: 96, height: 36, borderRadius: 1, bgcolor: "#cbd5e1" }} />
        <Box sx={{ width: 112, height: 36, borderRadius: 1, bgcolor: "#cbd5e1" }} />
      </Box>
    </Stack>
  );
}

export default function ChannelShieldPage() {
  const [protections, setProtections] = React.useState<ShieldProtection[]>([]);
  const [messages, setMessages] = React.useState<ShieldMessage[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [selected, setSelected] = React.useState<ShieldMessage | null>(null);
  const [channelFilter, setChannelFilter] = React.useState<string>("all");
  const [statusFilter, setStatusFilter] = React.useState<string>("quarantined");
  const [initialLoading, setInitialLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [health, setHealth] = React.useState<Array<Record<string, unknown>>>([]);
  const [settings, setSettings] = React.useState<Record<string, unknown> | null>(null);
  const [wizardOpen, setWizardOpen] = React.useState(false);
  const [wizardBusy, setWizardBusy] = React.useState(false);
  const [agentOs, setAgentOs] = React.useState<AgentOsPanel | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [employeeAction, setEmployeeAction] = React.useState<EmployeeAction | null>(null);
  const [mounted, setMounted] = React.useState(false);
  const loadedOnceRef = React.useRef(false);
  const [form, setForm] = React.useState({
    channel: "email",
    label: "",
    protection_key: "",
  });

  const load = React.useCallback(async () => {
    const firstLoad = !loadedOnceRef.current;
    if (firstLoad) {
      setInitialLoading(true);
    } else {
      setRefreshing(true);
    }
    setError(null);
    try {
      const channel = channelFilter === "all" ? undefined : channelFilter;
      const status = statusFilter === "all" ? undefined : statusFilter;
      const [prots, msgs, adapters, cfg, osPanel] = await Promise.all([
        fetchProtections(channel),
        fetchMessages({ channel, status }),
        fetchAdapterHealth(),
        fetchSettings(),
        fetchAgentOsPanel(),
      ]);
      setProtections(prots);
      setMessages(msgs);
      setHealth(adapters.health || []);
      setSettings(cfg);
      setAgentOs(osPanel);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setInitialLoading(false);
      setRefreshing(false);
      loadedOnceRef.current = true;
    }
  }, [channelFilter, statusFilter]);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  React.useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    setDetailLoading(true);
    void fetchMessage(selectedId)
      .then((msg) => setSelected(msg))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const openEmployeeDrawer = async (id: string) => {
    setError(null);
    try {
      const data = await fetchEmployeeAction(id);
      setEmployeeAction(data);
      setDrawerOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onCreate = async () => {
    setWizardBusy(true);
    setError(null);
    try {
      await createProtection({
        channel: form.channel,
        label: form.label || `${form.channel} protection`,
        protection_key: form.protection_key,
      });
      setWizardOpen(false);
      setForm({ channel: "email", label: "", protection_key: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWizardBusy(false);
    }
  };

  const shieldEnabled = Boolean(settings?.enabled);
  const channelLabel = channelFilter === "all" ? "all channels" : channelFilter;
  const statusLabel = statusFilter === "all" ? "all statuses" : statusFilter;
  const visibleHealth = React.useMemo(() => {
    if (channelFilter === "all") return health;
    return health.filter((item) => String(item.channel) === channelFilter);
  }, [channelFilter, health]);

  const setChannel = React.useCallback((next: string) => {
    setChannelFilter((current) => {
      if (current === next) return current;
      setSelectedId(null);
      setSelected(null);
      return next;
    });
  }, []);

  const setStatus = React.useCallback((next: string) => {
    setStatusFilter((current) => {
      if (current === next) return current;
      setSelectedId(null);
      setSelected(null);
      return next;
    });
  }, []);

  if (!mounted) {
    return (
      <div
        style={{
          minHeight: "100%",
          padding: 24,
          background: C.page,
          color: C.text,
          fontFamily: "Inter, system-ui, -apple-system, sans-serif",
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            margin: "0 auto",
            border: `1px solid ${C.panelBorder}`,
            borderRadius: 8,
            background: C.panel,
            padding: 24,
          }}
        >
          <strong>Channel Shield</strong>
          <p style={{ margin: "8px 0 0", color: C.muted }}>
            Loading inbound protection workspace...
          </p>
        </div>
      </div>
    );
  }

  return (
    <Box
      sx={{
        p: { xs: 2, md: 3 },
        maxWidth: 1400,
        mx: "auto",
        bgcolor: C.page,
        color: C.text,
        minHeight: "100%",
      }}
    >
      <Box
        sx={{
          mb: 3,
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          alignItems: { xs: "flex-start", sm: "center" },
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4" component="h1" sx={{ color: C.text, fontWeight: 900 }}>
            Channel Shield
          </Typography>
          <Typography sx={{ mt: 0.75, color: C.muted, maxWidth: 760, lineHeight: 1.5 }}>
            Inbound protection across email and messaging. Quarantine first; agents only see safe summaries.
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexShrink: 0 }}>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              onClick={() => void load()}
              sx={buttonOutlineSx}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              onClick={() => setWizardOpen(true)}
              sx={{ bgcolor: C.primary, fontWeight: 800, "&:hover": { bgcolor: "#1e40af" } }}
            >
              Add protection
            </Button>
          </Stack>
        </Box>
      </Box>

      {error ? (
        <Alert severity="error" sx={alertSx("error")}>
          {error}
        </Alert>
      ) : null}

      {settings && !shieldEnabled ? (
        <Alert severity="warning" sx={{ ...alertSx("warning"), fontWeight: 700 }}>
          Channel Shield is currently off (`enabled: false`). Protections can still be created; inbound
          scanning stays idle until you enable it in config.
        </Alert>
      ) : null}

      <Typography sx={{ mb: 1, fontWeight: 800, color: C.text }}>Channel</Typography>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} useFlexGap flexWrap="wrap">
        <FilterChip
          label="All channels"
          active={channelFilter === "all"}
          disabled={refreshing}
          onClick={() => setChannel("all")}
        />
        {CHANNELS.map((c) => (
          <FilterChip
            key={c}
            label={c}
            active={channelFilter === c}
            disabled={refreshing}
            onClick={() => setChannel(c)}
          />
        ))}
      </Stack>

      <Typography sx={{ mb: 1, fontWeight: 800, color: C.text }}>Status</Typography>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }} useFlexGap flexWrap="wrap">
        {["quarantined", "delivered", "released", "all"].map((s) => (
          <FilterChip
            key={s}
            label={s}
            active={statusFilter === s}
            disabled={refreshing}
            onClick={() => setStatus(s)}
          />
        ))}
      </Stack>

      <Box
        sx={{
          mb: 2,
          px: 1.5,
          py: 1,
          borderRadius: 1,
          bgcolor: refreshing ? C.infoSoft : C.panel,
          border: `1px solid ${refreshing ? C.infoBorder : C.panelBorder}`,
          color: refreshing ? C.infoText : C.muted,
          fontWeight: 700,
        }}
      >
        Showing {channelLabel}, {statusLabel}
        {refreshing ? " - updating..." : ` - ${messages.length} message${messages.length === 1 ? "" : "s"}`}
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "300px 1fr 1.1fr" },
          gap: 2,
          alignItems: "start",
        }}
      >
        <Stack spacing={2}>
          <Panel title="Protections">
            {initialLoading ? (
              <LoadingRows rows={3} />
            ) : protections.length === 0 ? (
              <EmptyNote
                title={channelFilter === "all" ? "No protections yet" : `No ${channelFilter} protections`}
                body={
                  channelFilter === "all"
                    ? "Click Add protection, pick a channel, and set a protection key (domain, team id, phone id, and so on)."
                    : `Click Add protection to create a ${channelFilter} protection, or switch back to All channels.`
                }
              />
            ) : (
              <List dense disablePadding>
                {protections.map((p) => (
                  <ListItem
                    key={p.id}
                    sx={{
                      mb: 1,
                      border: `1px solid ${C.softBorder}`,
                      borderRadius: 1,
                      bgcolor: C.panelAlt,
                    }}
                  >
                    <ListItemText
                      primary={p.label}
                      secondary={`${p.channel} · ${p.protection_key}${p.verified ? " · verified" : ""}`}
                      primaryTypographyProps={{ sx: { color: C.text, fontWeight: 700 } }}
                      secondaryTypographyProps={{ sx: { color: C.muted } }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Panel>

          <Panel title="Adapter health">
            {initialLoading ? (
              <LoadingRows rows={4} />
            ) : visibleHealth.length === 0 ? (
              <EmptyNote title="No adapter status" body="Refresh the page or check that the API is running on port 3333." />
            ) : (
              <Stack spacing={0.75}>
                {visibleHealth.map((h) => (
                  <Box
                    key={String(h.channel)}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 1,
                      py: 0.75,
                      px: 1,
                      borderRadius: 1,
                      bgcolor: C.panelAlt,
                      border: `1px solid ${C.softBorder}`,
                    }}
                  >
                    <Typography sx={{ color: C.text, fontWeight: 700 }}>{String(h.channel)}</Typography>
                    <Typography sx={{ color: h.ok ? "#166534" : C.danger, fontWeight: 800 }}>
                      {h.ok ? "ok" : "issue"}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            )}
            {settings ? (
              <Typography sx={{ mt: 1.5, color: C.muted, fontSize: "0.9rem" }}>
                fail-closed: {String(settings.fail_closed_default)} · enabled: {String(settings.enabled)} ·
                auto-release suspects: {String(settings.auto_release_suspects)}
              </Typography>
            ) : null}
          </Panel>

          <Panel title="Agent OS protection">
            {agentOs ? (
              <Stack spacing={1}>
                <Typography sx={{ color: C.text }}>
                  Protected agents: <b>{agentOs.protectedAgents.length}</b>
                </Typography>
                <Typography sx={{ color: C.text }}>
                  Blocked triggers: <b>{agentOs.blockedTriggers.length}</b>
                </Typography>
                <Typography sx={{ color: C.text }}>
                  Approval requests: <b>{agentOs.approvalRequests.length}</b>
                </Typography>
                <Typography sx={{ color: C.text }}>
                  Memory writes prevented: <b>{agentOs.memoryWritesPrevented.length}</b>
                </Typography>
                <Divider />
                {agentOs.protectedAgents.map((a) => (
                  <Box
                    key={String(a.agentId)}
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: C.panelAlt,
                      border: `1px solid ${C.softBorder}`,
                    }}
                  >
                    <Typography sx={{ color: C.text, fontWeight: 800 }}>
                      {String(a.label || a.agentId)}
                    </Typography>
                    <Typography sx={{ color: C.muted, fontSize: "0.85rem" }}>
                      view summary: {String(a.canViewSafeSummary)} · release after approval:{" "}
                      {String(a.canReleaseAfterApproval)} · destroy: {String(a.canDestroy)}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            ) : (
              <EmptyNote title="Loading" body="Fetching Agent OS protection status..." />
            )}
          </Panel>
        </Stack>

        <Panel title="Quarantine inbox">
          {initialLoading ? (
            <LoadingRows rows={6} />
          ) : messages.length === 0 ? (
            <EmptyNote
              title={`No ${statusLabel} messages`}
              body={
                channelFilter === "all"
                  ? "Held and delivered messages show up here after inbound traffic hits a protection."
                  : `No ${statusLabel} messages found for ${channelFilter}. Try All channels or another status.`
              }
            />
          ) : (
            <List dense disablePadding>
              {messages.map((m) => (
                <ListItemButton
                  key={m.id}
                  selected={selectedId === m.id}
                  onClick={() => setSelectedId(m.id)}
                  sx={{
                    mb: 1,
                    borderRadius: 1,
                    border: `1px solid ${selectedId === m.id ? C.selectedBorder : C.softBorder}`,
                    bgcolor: selectedId === m.id ? C.selected : C.panelAlt,
                    color: C.text,
                    "&.Mui-selected": { bgcolor: C.selected },
                    "&.Mui-selected:hover": { bgcolor: "#bfdbfe" },
                    "&:hover": { bgcolor: selectedId === m.id ? "#bfdbfe" : "#e2e8f0" },
                  }}
                >
                  <ListItemText
                    primary={m.subject || m.text_preview || "(no subject)"}
                    secondary={`${m.channel} · ${m.from} · ${m.status}`}
                    primaryTypographyProps={{ sx: { color: C.text, fontWeight: 700 } }}
                    secondaryTypographyProps={{ sx: { color: C.muted } }}
                  />
                  <Chip size="small" label={m.verdict || "pending"} color={verdictColor(m.verdict)} />
                </ListItemButton>
              ))}
            </List>
          )}
        </Panel>

        <Panel title="Message report">
          {detailLoading ? (
            <LoadingDetail />
          ) : !selected ? (
            <EmptyNote
              title="Nothing selected"
              body="Pick a quarantine item to review the pipeline report, safe summary, and actions."
            />
          ) : (
            <Box>
              <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} useFlexGap flexWrap="wrap">
                <Chip label={selected.channel} sx={chipSx()} />
                <Chip label={selected.status} sx={chipSx()} />
                <Chip label={selected.verdict || "n/a"} color={verdictColor(selected.verdict)} />
                {selected.policy_label ? (
                  <Chip label={selected.policy_label} sx={chipSx()} />
                ) : null}
              </Stack>
              <Typography sx={{ mb: 1, color: C.text }}>
                <b>From:</b> {selected.from || "(unknown)"}
              </Typography>
              <Typography sx={{ mb: 1, color: C.text }}>
                <b>Subject:</b> {selected.subject || "(none)"}
              </Typography>
              {selected.scout_ids?.length ? (
                <Typography sx={{ mb: 1, color: C.muted }}>
                  Scout ids: {selected.scout_ids.join(", ")}
                </Typography>
              ) : null}
              {selected.safe_summary ? (
                <Alert severity="warning" sx={alertSx("warning")}>
                  {selected.safe_summary}
                </Alert>
              ) : null}
              {selected.agent_safe_content ? (
                <Alert severity="info" sx={alertSx("info")}>
                  Agent-safe preview: {String(selected.agent_safe_content.text || "")}
                </Alert>
              ) : null}
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  overflow: "auto",
                  maxHeight: 260,
                  borderRadius: 1,
                  bgcolor: "#18181b",
                  color: "#f4f4f5",
                  border: `1px solid ${C.strongBorder}`,
                  fontSize: "0.8rem",
                }}
              >
                {JSON.stringify(selected.report || {}, null, 2)}
              </Box>
              <Stack direction="row" spacing={1} sx={{ mt: 2 }} useFlexGap flexWrap="wrap">
                <Button variant="contained" onClick={() => void openEmployeeDrawer(selected.id)}>
                  Employee action
                </Button>
                <Button
                  variant="outlined"
                  sx={buttonOutlineSx}
                  onClick={() =>
                    void releaseMessage(selected.id)
                      .then(load)
                      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
                  }
                >
                  Release
                </Button>
                <Button
                  color="error"
                  variant="outlined"
                  sx={{ fontWeight: 700 }}
                  onClick={() =>
                    void destroyMessage(selected.id)
                      .then(() => {
                        setSelectedId(null);
                        return load();
                      })
                      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
                  }
                >
                  Destroy
                </Button>
              </Stack>
            </Box>
          )}
        </Panel>
      </Box>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            bgcolor: C.panel,
            color: C.text,
            borderLeft: `1px solid ${C.panelBorder}`,
          },
        }}
      >
        <Box sx={{ width: { xs: 320, sm: 420 }, p: 2, bgcolor: C.panel, color: C.text, minHeight: "100%" }}>
          <Typography sx={{ mb: 1, fontWeight: 800, fontSize: "1.2rem" }}>Employee action</Typography>
          {!employeeAction ? (
            <Typography>No item loaded.</Typography>
          ) : (
            <Stack spacing={1.5}>
              <Chip
                label={`verdict: ${employeeAction.verdict || "n/a"}`}
                color={verdictColor(employeeAction.verdict)}
              />
              <Typography>
                <b>Policy:</b> {employeeAction.policyLabel || "n/a"}
              </Typography>
              <Typography>
                <b>Evidence:</b> {employeeAction.evidenceAccess}
              </Typography>
              <Typography>
                <b>Approval:</b> {employeeAction.approvalState}
              </Typography>
              <Alert severity="warning" sx={alertSx("warning")}>
                {employeeAction.safeSummary ||
                  String(employeeAction.agentSafeContent?.text || "No safe summary")}
              </Alert>
              <Typography sx={{ fontWeight: 800 }}>Allowed actions</Typography>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {employeeAction.allowedActions.map((a) => (
                  <Chip
                    key={a}
                    size="small"
                    label={a}
                    sx={chipSx()}
                  />
                ))}
              </Stack>
              <Typography sx={{ fontWeight: 800 }}>Audit trail</Typography>
              <List dense>
                {employeeAction.auditTrail.slice(0, 12).map((e) => (
                  <ListItem key={String(e.id)} sx={{ px: 0 }}>
                    <ListItemText
                      primary={String(e.event_type)}
                      secondary={String(e.created_at)}
                      primaryTypographyProps={{ sx: { color: C.text, fontWeight: 700 } }}
                      secondaryTypographyProps={{ sx: { color: C.muted } }}
                    />
                  </ListItem>
                ))}
              </List>
              <Button
                variant="outlined"
                sx={buttonOutlineSx}
                onClick={() =>
                  void requestApproval({ message_id: employeeAction.messageId, action: "release" })
                    .then(load)
                    .catch((err) => setError(err instanceof Error ? err.message : String(err)))
                }
              >
                Request release approval
              </Button>
            </Stack>
          )}
        </Box>
      </Drawer>

      <Dialog
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        fullWidth
        maxWidth="sm"
        PaperProps={{
          sx: {
            bgcolor: C.panel,
            color: C.text,
            border: `1px solid ${C.panelBorder}`,
          },
        }}
      >
        <DialogTitle sx={{ color: C.text, fontWeight: 900 }}>Add channel protection</DialogTitle>
        <DialogContent sx={{ color: C.text }}>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              label="Channel"
              value={form.channel}
              onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}
              sx={textFieldSx}
            >
              {CHANNELS.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Label"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              sx={textFieldSx}
            />
            <TextField
              label="Protection key"
              helperText="Domain, team_id, tenant_id, phone_number_id, guild_id, inbound number, or embed key"
              value={form.protection_key}
              onChange={(e) => setForm((f) => ({ ...f, protection_key: e.target.value }))}
              required
              sx={textFieldSx}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWizardOpen(false)} sx={{ color: C.text, fontWeight: 800 }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={wizardBusy || !form.protection_key}
            onClick={() => void onCreate()}
            sx={{ bgcolor: C.primary, fontWeight: 800, "&:hover": { bgcolor: "#1e40af" } }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
