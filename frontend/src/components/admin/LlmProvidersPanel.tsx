"use client";

import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import StarOutlineIcon from "@mui/icons-material/StarOutline";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import type { CustomProvider } from "@/lib/admin-workspace-api";

type ProviderCatalogItem = { id: string; label: string };

type ProviderState = {
  connected: boolean;
  default_model?: string | null;
  is_default?: boolean;
};

type LlmProvidersPanelProps = {
  providerRows: ProviderCatalogItem[];
  providers: Record<string, ProviderState> | undefined;
  customProviders: CustomProvider[];
  busy: boolean;
  onConfigureBuiltin: (providerId: string) => void;
  onRemoveBuiltin: (providerId: string) => void;
  onMakeDefault: (providerId: string) => void;
  onConfigureCustom: (provider?: CustomProvider) => void;
  onRemoveCustom: (providerId: string) => void;
};

type ProviderRowProps = {
  name: string;
  connected: boolean;
  isDefault: boolean;
  detail?: string | null;
  busy: boolean;
  onConfigure: () => void;
  onMakeDefault?: () => void;
  onRemove?: () => void;
};

function ProviderRow({ name, connected, isDefault, detail, busy, onConfigure, onMakeDefault, onRemove }: ProviderRowProps) {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);

  const closeMenu = () => setAnchorEl(null);

  if (!connected) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, px: 2, py: 1.25 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Not configured
          </Typography>
        </Box>
        <Button size="small" variant="text" onClick={onConfigure} sx={{ flexShrink: 0 }}>
          Configure
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: 2, py: 1.25 }}>
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {name}
          </Typography>
          {isDefault ? <Chip label="Default" size="small" color="primary" /> : null}
        </Stack>
        {detail ? (
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {detail}
          </Typography>
        ) : null}
      </Box>
      <IconButton
        size="small"
        aria-label={`${name} actions`}
        disabled={busy}
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={{ flexShrink: 0 }}
      >
        <MoreVertIcon fontSize="small" />
      </IconButton>
      <Menu anchorEl={anchorEl} open={menuOpen} onClose={closeMenu}>
        <MenuItem
          onClick={() => {
            closeMenu();
            onConfigure();
          }}
        >
          Edit
        </MenuItem>
        {!isDefault && onMakeDefault ? (
          <MenuItem
            disabled={busy}
            onClick={() => {
              closeMenu();
              onMakeDefault();
            }}
          >
            <ListItemIcon>
              <StarOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Set as default</ListItemText>
          </MenuItem>
        ) : null}
        {onRemove ? (
          <MenuItem
            disabled={busy}
            onClick={() => {
              closeMenu();
              onRemove();
            }}
            sx={{ color: "error.main" }}
          >
            <ListItemIcon sx={{ color: "inherit" }}>
              <DeleteOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Remove</ListItemText>
          </MenuItem>
        ) : null}
      </Menu>
    </Box>
  );
}

function ProviderList({ children }: { children: React.ReactNode }) {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 1,
        overflow: "hidden",
        bgcolor: "background.paper",
      }}
    >
      {children}
    </Box>
  );
}

function ProviderSection({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2} sx={{ mb: 1.5 }}>
        <Box>
          <Typography variant="subtitle2">{title}</Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
            {description}
          </Typography>
        </Box>
        {action}
      </Stack>
      {children}
    </Box>
  );
}

export default function LlmProvidersPanel({
  providerRows,
  providers,
  customProviders,
  busy,
  onConfigureBuiltin,
  onRemoveBuiltin,
  onMakeDefault,
  onConfigureCustom,
  onRemoveCustom,
}: LlmProvidersPanelProps) {
  return (
    <Stack spacing={3}>
      <ProviderSection
        title="Built-in providers"
        description="API keys for known providers. Keys are stored in your environment file."
      >
        <ProviderList>
          {providerRows.map((provider, index) => {
            const state = providers?.[provider.id];
            return (
              <React.Fragment key={provider.id}>
                {index > 0 ? <Divider /> : null}
                <ProviderRow
                  name={provider.label}
                  connected={Boolean(state?.connected)}
                  isDefault={Boolean(state?.is_default)}
                  detail={state?.default_model}
                  busy={busy}
                  onConfigure={() => onConfigureBuiltin(provider.id)}
                  onMakeDefault={() => onMakeDefault(provider.id)}
                  onRemove={() => onRemoveBuiltin(provider.id)}
                />
              </React.Fragment>
            );
          })}
        </ProviderList>
      </ProviderSection>

      <ProviderSection
        title="Custom providers"
        description="OpenAI-compatible endpoints such as Ollama, LM Studio, vLLM, or RunPod."
        action={
          customProviders.length ? (
            <Button size="small" startIcon={<AddIcon />} onClick={() => onConfigureCustom()} sx={{ flexShrink: 0 }}>
              Add
            </Button>
          ) : null
        }
      >
        {customProviders.length ? (
          <ProviderList>
            {customProviders.map((provider, index) => (
              <React.Fragment key={provider.id}>
                {index > 0 ? <Divider /> : null}
                <ProviderRow
                  name={provider.name}
                  connected={Boolean(provider.connected)}
                  isDefault={Boolean(provider.is_default)}
                  detail={provider.default_model || provider.base_url}
                  busy={busy}
                  onConfigure={() => onConfigureCustom(provider)}
                  onMakeDefault={() => onMakeDefault(`custom/${provider.id}`)}
                  onRemove={() => onRemoveCustom(provider.id)}
                />
              </React.Fragment>
            ))}
          </ProviderList>
        ) : (
          <Box
            sx={{
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              borderStyle: "dashed",
              px: 2,
              py: 3,
              textAlign: "center",
            }}
          >
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              No custom providers yet.
            </Typography>
            <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => onConfigureCustom()}>
              Add custom provider
            </Button>
          </Box>
        )}
      </ProviderSection>
    </Stack>
  );
}
