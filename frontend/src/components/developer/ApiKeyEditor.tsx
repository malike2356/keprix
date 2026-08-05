"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useEffect, useMemo, useState } from "react";
import type {
  CreateApiKeyPayload,
  DeveloperApiKey,
  PermissionMode,
  ScopeCatalog,
  UpdateApiKeyPayload,
} from "@/lib/developer-api";

const EXPIRE_OPTIONS: Array<{ label: string; days: number | null }> = [
  { label: "Never", days: null },
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "1 year", days: 365 },
];

type Props = {
  open: boolean;
  mode: "create" | "edit";
  catalog: ScopeCatalog | null;
  models: string[];
  initial?: DeveloperApiKey | null;
  createdSecret?: string | null;
  saving?: boolean;
  onClose: () => void;
  onCreate: (payload: CreateApiKeyPayload) => Promise<void>;
  onUpdate: (keyId: string, payload: UpdateApiKeyPayload) => Promise<void>;
};

function ModeButtons({
  modes,
  value,
  onChange,
  disabled,
}: {
  modes: PermissionMode[];
  value: PermissionMode;
  onChange: (next: PermissionMode) => void;
  disabled?: boolean;
}) {
  const options = modes.includes("none") ? modes : (["none", ...modes] as PermissionMode[]);
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value}
      disabled={disabled}
      onChange={(_, next: PermissionMode | null) => {
        if (next) onChange(next);
      }}
      sx={{ flexWrap: "wrap" }}
    >
      {options.map((mode) => (
        <ToggleButton key={mode} value={mode} sx={{ textTransform: "none", px: 1.25 }}>
          {mode === "none" ? "No Access" : mode === "access" ? "Access" : mode === "read" ? "Read" : "Write"}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}

export default function ApiKeyEditor({
  open,
  mode,
  catalog,
  models,
  initial,
  createdSecret,
  saving,
  onClose,
  onCreate,
  onUpdate,
}: Props) {
  const defaults = catalog?.defaults;
  const [name, setName] = useState("");
  const [expireDays, setExpireDays] = useState<number | "keep" | null>("keep");
  const [restrictKey, setRestrictKey] = useState(true);
  const [monthlyLimit, setMonthlyLimit] = useState<string>("");
  const [permissions, setPermissions] = useState<Record<string, PermissionMode>>({});
  const [allowedModels, setAllowedModels] = useState<string[]>(["keprix"]);
  const [allowedIps, setAllowedIps] = useState("");
  const [autoDisable, setAutoDisable] = useState(true);

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && initial) {
      setName(initial.name || "");
      setExpireDays("keep");
      setRestrictKey(initial.restrict_key ?? true);
      setMonthlyLimit(
        initial.monthly_limit == null || initial.monthly_limit === undefined
          ? ""
          : String(initial.monthly_limit),
      );
      const perms: Record<string, PermissionMode> = {};
      for (const [key, value] of Object.entries(initial.permissions || {})) {
        perms[key] = (value as PermissionMode) || "none";
      }
      setPermissions(perms);
      setAllowedModels(initial.allowed_models?.length ? initial.allowed_models : ["keprix"]);
      setAllowedIps((initial.allowed_ips || []).join(", "));
      setAutoDisable(initial.auto_disable_if_leaked ?? true);
      return;
    }
    setName("");
    setExpireDays(null);
    setRestrictKey(defaults?.restrict_key ?? true);
    setMonthlyLimit("");
    const seeded: Record<string, PermissionMode> = {};
    for (const [key, value] of Object.entries(defaults?.permissions || {})) {
      seeded[key] = (value as PermissionMode) || "none";
    }
    setPermissions(seeded);
    setAllowedModels(defaults?.allowed_models?.length ? defaults.allowed_models : ["keprix"]);
    setAllowedIps("");
    setAutoDisable(defaults?.auto_disable_if_leaked ?? true);
  }, [open, mode, initial, defaults]);

  const groups = catalog?.groups || [];

  const title = useMemo(() => {
    if (createdSecret) return "API key created";
    return mode === "edit" ? "Edit API key" : "Create API key";
  }, [createdSecret, mode]);

  const submit = async () => {
    const ips = allowedIps
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean);
    const limit = monthlyLimit.trim() === "" ? null : Number(monthlyLimit);
    if (mode === "create") {
      await onCreate({
        name: name.trim(),
        restrict_key: restrictKey,
        expire_after_days: typeof expireDays === "number" ? expireDays : null,
        monthly_limit: Number.isFinite(limit as number) ? (limit as number) : null,
        permissions: restrictKey ? permissions : {},
        allowed_models: restrictKey ? allowedModels : [],
        allowed_ips: ips,
        auto_disable_if_leaked: autoDisable,
        enabled: true,
      });
      return;
    }
    if (!initial) return;
    const payload: UpdateApiKeyPayload = {
      name: name.trim(),
      restrict_key: restrictKey,
      monthly_limit: Number.isFinite(limit as number) ? (limit as number) : null,
      permissions: restrictKey ? permissions : {},
      allowed_models: restrictKey ? allowedModels : [],
      allowed_ips: ips,
      auto_disable_if_leaked: autoDisable,
    };
    if (expireDays === null) {
      payload.clear_expiry = true;
    } else if (typeof expireDays === "number") {
      payload.expire_after_days = expireDays;
    }
    await onUpdate(initial.id, payload);
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: "100%", sm: 480 }, p: 0 } }}
    >
      <Box sx={{ p: 2.5, borderBottom: 1, borderColor: "divider" }}>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          Deny-by-default scopes. Only grant what each app needs.
        </Typography>
      </Box>

      <Box sx={{ p: 2.5, overflow: "auto", flex: 1 }}>
        {createdSecret ? (
          <Stack spacing={2}>
            <Alert severity="warning">Copy this secret now. It will not be shown again.</Alert>
            <Box
              sx={{
                p: 2,
                borderRadius: 1,
                bgcolor: "background.default",
                border: 1,
                borderColor: "divider",
                fontFamily: "monospace",
                fontSize: "0.8rem",
                wordBreak: "break-all",
              }}
            >
              {createdSecret}
            </Box>
            <Button variant="contained" onClick={onClose}>
              Done
            </Button>
          </Stack>
        ) : (
          <Stack spacing={2.5}>
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              fullWidth
              autoFocus
              placeholder="my-app-integration"
            />

            <TextField
              select
              label="Expire After"
              value={expireDays === "keep" ? "keep" : expireDays == null ? "never" : String(expireDays)}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "keep") setExpireDays("keep");
                else if (v === "never") setExpireDays(null);
                else setExpireDays(Number(v));
              }}
              fullWidth
              helperText={
                mode === "edit" && initial?.expires_at
                  ? `Current expiry: ${initial.expires_at}`
                  : mode === "edit"
                    ? "Current expiry: Never"
                    : undefined
              }
            >
              {mode === "edit" ? <MenuItem value="keep">Keep current</MenuItem> : null}
              {EXPIRE_OPTIONS.map((opt) => (
                <MenuItem key={opt.label} value={opt.days == null ? "never" : String(opt.days)}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>

            <FormControlLabel
              control={<Switch checked={restrictKey} onChange={(e) => setRestrictKey(e.target.checked)} />}
              label="Restrict Key"
            />
            <Typography variant="caption" color="text.secondary">
              When on, only the endpoint permissions below apply. When off, the key can call any
              granted public and scoped workspace route (still rate-limited).
            </Typography>

            <TextField
              label="Usage Limits (Credits)"
              value={monthlyLimit}
              onChange={(e) => setMonthlyLimit(e.target.value)}
              fullWidth
              placeholder="Unlimited"
              helperText="Per credit refresh period (monthly request budget). Leave blank for unlimited."
              type="number"
            />

            {restrictKey ? (
              <>
                <Divider />
                <Typography variant="subtitle2">Endpoints</Typography>
                {groups.map((group) => (
                  <Stack key={group.group} spacing={1.5}>
                    <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase" }}>
                      {group.group}
                    </Typography>
                    {group.items.map((item) => (
                      <Box
                        key={item.id}
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 0.75,
                          py: 0.5,
                        }}
                      >
                        <Typography variant="body2" fontWeight={600}>
                          {item.label}
                          {item.sensitive ? (
                            <Typography component="span" variant="caption" color="warning.main" sx={{ ml: 1 }}>
                              sensitive
                            </Typography>
                          ) : null}
                        </Typography>
                        <ModeButtons
                          modes={item.modes as PermissionMode[]}
                          value={(permissions[item.id] as PermissionMode) || "none"}
                          onChange={(next) => setPermissions((prev) => ({ ...prev, [item.id]: next }))}
                        />
                      </Box>
                    ))}
                  </Stack>
                ))}

                <TextField
                  select
                  label="Allowed models"
                  value={allowedModels[0] || "keprix"}
                  onChange={(e) => setAllowedModels([e.target.value])}
                  fullWidth
                  helperText="Restricted keys may only use listed models."
                >
                  {(models.length ? models : ["keprix"]).map((model) => (
                    <MenuItem key={model} value={model}>
                      {model}
                    </MenuItem>
                  ))}
                </TextField>
              </>
            ) : null}

            <Divider />
            <TextField
              label="Restrict by IP address"
              value={allowedIps}
              onChange={(e) => setAllowedIps(e.target.value)}
              fullWidth
              multiline
              minRows={2}
              placeholder="203.0.113.10, 198.51.100.*"
              helperText="Comma or newline separated. Leave blank to allow any IP."
            />

            <FormControlLabel
              control={<Switch checked={autoDisable} onChange={(e) => setAutoDisable(e.target.checked)} />}
              label="Auto-disable if leaked"
            />
            <Typography variant="caption" color="text.secondary">
              If the key is detected as publicly exposed, or{" "}
              <code>POST /v1/keys/self-disable</code> is called with this key, Keprix will disable it.
              Turn this off to keep the key working even if it is found leaked.
            </Typography>

            <Stack direction="row" spacing={1} justifyContent="flex-end">
              <Button onClick={onClose}>Cancel</Button>
              <Button
                variant="contained"
                disabled={saving || !name.trim()}
                onClick={() => void submit()}
              >
                {saving ? "Saving..." : mode === "edit" ? "Save" : "Create key"}
              </Button>
            </Stack>
          </Stack>
        )}
      </Box>
    </Drawer>
  );
}
