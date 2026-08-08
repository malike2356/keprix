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
import { alpha, useTheme, type Theme } from "@mui/material/styles";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
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

const STATUSES = ["quarantined", "delivered", "released", "all"] as const;

type ShieldColors = {
  page: string;
  panel: string;
  panelAlt: string;
  panelBorder: string;
  text: string;
  muted: string;
  softBorder: string;
  selected: string;
  selectedBorder: string;
  primary: string;
  primaryDark: string;
  danger: string;
  dangerSoft: string;
  warningText: string;
  warningSoft: string;
  warningBorder: string;
  infoText: string;
  infoSoft: string;
  infoBorder: string;
  successText: string;
  hover: string;
};

function shieldColors(theme: Theme): ShieldColors {
  const p = theme.palette;
  const dark = p.mode === "dark";
  return {
    page: p.background.default,
    panel: p.background.paper,
    panelAlt: dark ? alpha(p.common.white, 0.04) : alpha(p.common.black, 0.03),
    panelBorder: p.divider,
    text: p.text.primary,
    muted: p.text.secondary,
    softBorder: p.divider,
    selected: alpha(p.primary.main, dark ? 0.22 : 0.12),
    selectedBorder: p.primary.main,
    primary: p.primary.main,
    primaryDark: p.primary.dark,
    danger: p.error.main,
    dangerSoft: alpha(p.error.main, dark ? 0.16 : 0.08),
    warningText: p.warning.main,
    warningSoft: alpha(p.warning.main, dark ? 0.16 : 0.1),
    warningBorder: alpha(p.warning.main, 0.45),
    infoText: p.info.main,
    infoSoft: alpha(p.info.main, dark ? 0.16 : 0.08),
    infoBorder: alpha(p.info.main, 0.45),
    successText: p.success.main,
    hover: dark ? alpha(p.common.white, 0.06) : alpha(p.common.black, 0.04),
  };
}

function fieldSx(c: ShieldColors) {
  return {
    minWidth: 140,
    "& .MuiInputBase-root": { bgcolor: c.panel, color: c.text },
    "& .MuiInputLabel-root": { color: c.muted },
    "& .MuiOutlinedInput-notchedOutline": { borderColor: c.softBorder },
  };
}

function alertSx(c: ShieldColors, kind: "warning" | "info" | "error") {
  if (kind === "error") {
    return {
      mb: 2,
      color: c.danger,
      bgcolor: c.dangerSoft,
      border: `1px solid ${c.danger}`,
      "& .MuiAlert-icon": { color: c.danger },
    };
  }
  if (kind === "info") {
    return {
      mb: 2,
      whiteSpace: "pre-wrap" as const,
      color: c.infoText,
      bgcolor: c.infoSoft,
      border: `1px solid ${c.infoBorder}`,
      "& .MuiAlert-icon": { color: c.primary },
    };
  }
  return {
    mb: 2,
    whiteSpace: "pre-wrap" as const,
    color: c.warningText,
    bgcolor: c.warningSoft,
    border: `1px solid ${c.warningBorder}`,
    "& .MuiAlert-icon": { color: c.warningText },
  };
}

function verdictColor(verdict: string | null): "default" | "success" | "warning" | "error" {
  if (verdict === "clean") return "success";
  if (verdict === "suspect") return "warning";
  if (verdict === "malicious" || verdict === "error") return "error";
  return "default";
}

function Section({
  title,
  count,
  children,
  c,
}: {
  title: string;
  count?: string;
  children: React.ReactNode;
  c: ShieldColors;
}) {
  return (
    <Box
      sx={{
        border: `1px solid ${c.panelBorder}`,
        borderRadius: 1,
        bgcolor: c.panel,
        color: c.text,
        display: "flex",
        flexDirection: "column",
        minHeight: { md: 520 },
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.25,
          borderBottom: `1px solid ${c.panelBorder}`,
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Typography sx={{ fontWeight: 700, fontSize: "0.95rem" }}>{title}</Typography>
        {count ? (
          <Typography sx={{ color: c.muted, fontSize: "0.8rem" }}>{count}</Typography>
        ) : null}
      </Box>
      <Box sx={{ p: 2, flex: 1, overflow: "auto" }}>{children}</Box>
    </Box>
  );
}

function QuietEmpty({ title, body }: { title: string; body: string }) {
  const theme = useTheme();
  const c = shieldColors(theme);
  return (
    <Box sx={{ py: 6, px: 1, textAlign: "center" }}>
      <Typography sx={{ fontWeight: 600, color: c.text, mb: 0.5 }}>{title}</Typography>
      <Typography sx={{ color: c.muted, fontSize: "0.9rem", lineHeight: 1.5, maxWidth: 360, mx: "auto" }}>
        {body}
      </Typography>
    </Box>
  );
}

export default function ChannelShieldPage() {
  const theme = useTheme();
  const C = React.useMemo(() => shieldColors(theme), [theme]);
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
  const [showMeta, setShowMeta] = React.useState(false);
  const loadedOnceRef = React.useRef(false);
  const [form, setForm] = React.useState({
    channel: "email",
    label: "",
    protection_key: "",
  });

  const load = React.useCallback(async () => {
    const firstLoad = !loadedOnceRef.current;
    if (firstLoad) setInitialLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const channel = channelFilter === "all" ? undefined : channelFilter;
      const status = statusFilter === "all" ? undefined : statusFilter;
      const [protectionsResult, messagesResult, healthResult, settingsResult, agentOsResult] = await Promise.allSettled([
        fetchProtections(channel),
        fetchMessages({ channel, status }),
        fetchAdapterHealth(),
        fetchSettings(),
        fetchAgentOsPanel(),
      ]);
      const results = [protectionsResult, messagesResult, healthResult, settingsResult, agentOsResult];
      const labels = ["protections", "messages", "adapters", "settings", "agent OS"] as const;
      const failures: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "rejected") {
          const reason =
            result.reason instanceof Error ? result.reason.message : String(result.reason);
          failures.push(`${labels[index]}: ${reason}`);
          return;
        }
        if (index === 0 && protectionsResult.status === "fulfilled") setProtections(protectionsResult.value);
        if (index === 1 && messagesResult.status === "fulfilled") setMessages(messagesResult.value);
        if (index === 2 && healthResult.status === "fulfilled") setHealth(healthResult.value.health || []);
        if (index === 3 && settingsResult.status === "fulfilled") setSettings(settingsResult.value);
        if (index === 4 && agentOsResult.status === "fulfilled") setAgentOs(agentOsResult.value);
      });
      if (failures.length) setError(failures.join(" | "));
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
  const adaptersOk = health.filter((h) => h.ok).length;
  const adaptersTotal = health.length;
  const metaLine = [
    `${protections.length} protection${protections.length === 1 ? "" : "s"}`,
    adaptersTotal ? `adapters ${adaptersOk}/${adaptersTotal} ok` : null,
    agentOs ? `${agentOs.protectedAgents.length} agents guarded` : null,
    settings ? (shieldEnabled ? "shield on" : "shield off") : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, maxWidth: 1280, mx: "auto", bgcolor: C.page, color: C.text }}>
      <PageHeader
        title="Channel Shield"
        description="Quarantine inbound mail and messages first. Agents only see safe summaries."
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" size="small" disabled={refreshing} onClick={() => void load()}>
              Refresh
            </Button>
            <Button variant="contained" size="small" onClick={() => setWizardOpen(true)}>
              Add protection
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" sx={alertSx(C, "error")}>
          {error}
        </Alert>
      ) : null}

      {settings && !shieldEnabled ? (
        <Alert severity="warning" sx={alertSx(C, "warning")}>
          Channel Shield is off. Protections can still be created; scanning stays idle until enabled.
        </Alert>
      ) : null}

      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        alignItems={{ xs: "stretch", sm: "center" }}
        sx={{ mb: 2 }}
      >
        <TextField
          select
          size="small"
          label="Channel"
          value={channelFilter}
          disabled={refreshing}
          onChange={(e) => {
            setChannelFilter(e.target.value);
            setSelectedId(null);
            setSelected(null);
          }}
          sx={fieldSx(C)}
        >
          <MenuItem value="all">All channels</MenuItem>
          {CHANNELS.map((ch) => (
            <MenuItem key={ch} value={ch}>
              {ch}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Status"
          value={statusFilter}
          disabled={refreshing}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setSelectedId(null);
            setSelected(null);
          }}
          sx={fieldSx(C)}
        >
          {STATUSES.map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
        <Typography sx={{ color: C.muted, fontSize: "0.85rem", flex: 1 }}>
          {refreshing
            ? "Updating…"
            : initialLoading
              ? "Loading…"
              : `${messages.length} message${messages.length === 1 ? "" : "s"}`}
        </Typography>
        <Button size="small" onClick={() => setShowMeta((v) => !v)} sx={{ color: C.muted }}>
          {showMeta ? "Hide details" : "Details"}
        </Button>
      </Stack>

      {showMeta ? (
        <Box
          sx={{
            mb: 2,
            px: 2,
            py: 1.5,
            borderRadius: 1,
            border: `1px solid ${C.panelBorder}`,
            bgcolor: C.panel,
          }}
        >
          <Typography sx={{ color: C.muted, fontSize: "0.85rem", mb: 1.25 }}>{metaLine}</Typography>
          {protections.length === 0 ? (
            <Typography sx={{ color: C.muted, fontSize: "0.9rem" }}>
              No protections yet. Use Add protection to bind a channel key.
            </Typography>
          ) : (
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {protections.map((p) => (
                <Chip
                  key={p.id}
                  size="small"
                  variant="outlined"
                  label={`${p.channel}: ${p.label || p.protection_key}`}
                />
              ))}
            </Stack>
          )}
          {agentOs && agentOs.blockedTriggers.length + agentOs.approvalRequests.length > 0 ? (
            <Typography sx={{ mt: 1, color: C.muted, fontSize: "0.85rem" }}>
              {agentOs.blockedTriggers.length} blocked · {agentOs.approvalRequests.length} approvals ·{" "}
              {agentOs.memoryWritesPrevented.length} memory blocks
            </Typography>
          ) : null}
        </Box>
      ) : (
        <Typography sx={{ mb: 2, color: C.muted, fontSize: "0.8rem" }}>{metaLine}</Typography>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 2,
          alignItems: "stretch",
        }}
      >
        <Section
          title="Inbox"
          count={initialLoading ? undefined : String(messages.length)}
          c={C}
        >
          {initialLoading ? (
            <Typography sx={{ color: C.muted }}>Loading inbox…</Typography>
          ) : messages.length === 0 ? (
            <QuietEmpty
              title="Inbox empty"
              body="Quarantined and filtered messages appear here after inbound traffic hits a protection."
            />
          ) : (
            <List dense disablePadding>
              {messages.map((m) => {
                const active = selectedId === m.id;
                return (
                  <ListItemButton
                    key={m.id}
                    selected={active}
                    onClick={() => setSelectedId(m.id)}
                    sx={{
                      mb: 0.75,
                      borderRadius: 1,
                      border: `1px solid ${active ? C.selectedBorder : "transparent"}`,
                      bgcolor: active ? C.selected : "transparent",
                      "&:hover": { bgcolor: active ? C.selected : C.hover },
                      "&.Mui-selected": { bgcolor: C.selected },
                      "&.Mui-selected:hover": { bgcolor: C.selected },
                    }}
                  >
                    <ListItemText
                      primary={m.subject || m.text_preview || "(no subject)"}
                      secondary={`${m.channel} · ${m.from} · ${m.status}`}
                      primaryTypographyProps={{
                        sx: {
                          color: C.text,
                          fontWeight: 600,
                          fontSize: "0.9rem",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        },
                      }}
                      secondaryTypographyProps={{ sx: { color: C.muted, fontSize: "0.8rem" } }}
                    />
                    <Chip size="small" label={m.verdict || "pending"} color={verdictColor(m.verdict)} />
                  </ListItemButton>
                );
              })}
            </List>
          )}
        </Section>

        <Section title="Report" c={C}>
          {detailLoading ? (
            <Typography sx={{ color: C.muted }}>Loading report…</Typography>
          ) : !selected ? (
            <QuietEmpty title="Select a message" body="Choose an inbox item to review the safe summary and actions." />
          ) : (
            <Stack spacing={1.5}>
              <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                <Chip size="small" label={selected.channel} variant="outlined" />
                <Chip size="small" label={selected.status} variant="outlined" />
                <Chip size="small" label={selected.verdict || "n/a"} color={verdictColor(selected.verdict)} />
              </Stack>
              <Box>
                <Typography sx={{ color: C.muted, fontSize: "0.8rem" }}>From</Typography>
                <Typography sx={{ color: C.text }}>{selected.from || "(unknown)"}</Typography>
              </Box>
              <Box>
                <Typography sx={{ color: C.muted, fontSize: "0.8rem" }}>Subject</Typography>
                <Typography sx={{ color: C.text }}>{selected.subject || "(none)"}</Typography>
              </Box>
              {selected.safe_summary ? (
                <Alert severity="warning" sx={alertSx(C, "warning")}>
                  {selected.safe_summary}
                </Alert>
              ) : null}
              {selected.agent_safe_content?.text ? (
                <Alert severity="info" sx={alertSx(C, "info")}>
                  {String(selected.agent_safe_content.text)}
                </Alert>
              ) : null}
              <Box
                sx={{
                  p: 1.5,
                  overflow: "auto",
                  maxHeight: 220,
                  borderRadius: 1,
                  bgcolor: C.panelAlt,
                  color: C.text,
                  border: `1px solid ${C.softBorder}`,
                }}
              >
                <StructuredDataView value={selected.report || {}} emptyLabel="No report" />
              </Box>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                <Button size="small" variant="contained" onClick={() => void openEmployeeDrawer(selected.id)}>
                  Employee action
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    void releaseMessage(selected.id)
                      .then(load)
                      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
                  }
                >
                  Release
                </Button>
                <Button
                  size="small"
                  color="error"
                  variant="outlined"
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
            </Stack>
          )}
        </Section>
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
        <Box sx={{ width: { xs: 320, sm: 400 }, p: 2.5, minHeight: "100%" }}>
          <Typography sx={{ mb: 2, fontWeight: 700, fontSize: "1.1rem" }}>Employee action</Typography>
          {!employeeAction ? (
            <Typography sx={{ color: C.muted }}>No item loaded.</Typography>
          ) : (
            <Stack spacing={1.5}>
              <Chip
                size="small"
                label={employeeAction.verdict || "n/a"}
                color={verdictColor(employeeAction.verdict)}
              />
              <Typography sx={{ fontSize: "0.9rem" }}>
                Policy: {employeeAction.policyLabel || "n/a"}
              </Typography>
              <Typography sx={{ fontSize: "0.9rem" }}>
                Evidence: {employeeAction.evidenceAccess}
              </Typography>
              <Typography sx={{ fontSize: "0.9rem" }}>
                Approval: {employeeAction.approvalState}
              </Typography>
              <Alert severity="warning" sx={alertSx(C, "warning")}>
                {employeeAction.safeSummary ||
                  String(employeeAction.agentSafeContent?.text || "No safe summary")}
              </Alert>
              {employeeAction.allowedActions.length ? (
                <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                  {employeeAction.allowedActions.map((a) => (
                    <Chip key={a} size="small" variant="outlined" label={a} />
                  ))}
                </Stack>
              ) : null}
              <Divider />
              <Typography sx={{ fontWeight: 600, fontSize: "0.85rem" }}>Audit</Typography>
              <List dense disablePadding>
                {employeeAction.auditTrail.slice(0, 8).map((e) => (
                  <ListItem key={String(e.id)} sx={{ px: 0 }}>
                    <ListItemText
                      primary={String(e.event_type)}
                      secondary={String(e.created_at)}
                      primaryTypographyProps={{ sx: { color: C.text, fontSize: "0.85rem" } }}
                      secondaryTypographyProps={{ sx: { color: C.muted, fontSize: "0.75rem" } }}
                    />
                  </ListItem>
                ))}
              </List>
              <Button
                size="small"
                variant="outlined"
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
        PaperProps={{ sx: { bgcolor: C.panel, color: C.text, border: `1px solid ${C.panelBorder}` } }}
      >
        <DialogTitle sx={{ fontWeight: 700 }}>Add channel protection</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              size="small"
              label="Channel"
              value={form.channel}
              onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value }))}
              sx={fieldSx(C)}
            >
              {CHANNELS.map((ch) => (
                <MenuItem key={ch} value={ch}>
                  {ch}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Label"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              sx={fieldSx(C)}
            />
            <TextField
              size="small"
              label="Protection key"
              helperText="Domain, team id, tenant id, phone number id, guild id, or inbound number"
              value={form.protection_key}
              onChange={(e) => setForm((f) => ({ ...f, protection_key: e.target.value }))}
              required
              sx={fieldSx(C)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWizardOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={wizardBusy || !form.protection_key}
            onClick={() => void onCreate()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
