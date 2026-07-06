"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid2";
import Menu from "@mui/material/Menu";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { IconDice3, IconMoon, IconPalette, IconSun } from "@tabler/icons-react";
import IconButton from "@mui/material/IconButton";
import { alpha } from "@mui/material/styles";
import * as React from "react";
import { useThemeMode } from "@/components/providers/ThemeRegistry";
import { pickRandomSkinId, readRecentSkinIds } from "@/theme/theme-recent";

export const themePickerMenuPaperSx = { width: 320, maxWidth: "92vw", p: 1.5 };

type ThemeAppearanceControlsProps = {
  onSkinSelect?: () => void;
};

export function ThemeAppearanceControls({ onSkinSelect }: ThemeAppearanceControlsProps) {
  const { mode, skin, skins, setMode, setSkin } = useThemeMode();
  const [recentIds, setRecentIds] = React.useState<string[]>([]);

  React.useEffect(() => {
    setRecentIds(readRecentSkinIds());
  }, [skin]);

  const recentSkins = recentIds
    .map((id) => skins.find((item) => item.id === id))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
    .slice(0, 4);

  const onSurprise = () => {
    const next = pickRandomSkinId(skin, skins);
    setSkin(next);
    onSkinSelect?.();
  };

  const renderSkinButton = (item: (typeof skins)[number], compact = false) => {
    const selected = item.id === skin;
    return (
      <Tooltip title={item.label}>
        <Button
          fullWidth
          variant={selected ? "contained" : "outlined"}
          onClick={() => {
            setSkin(item.id);
            onSkinSelect?.();
          }}
          aria-pressed={selected}
          sx={{
            minHeight: compact ? 44 : 56,
            p: 0.5,
            flexDirection: "column",
            gap: 0.5,
            textTransform: "none",
            transition: "transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease",
            transform: selected ? "scale(1.02)" : "scale(1)",
            boxShadow: selected ? `0 0 0 2px ${alpha(item.primary, 0.35)}` : "none",
            "&:hover": {
              transform: selected ? "scale(1.04)" : "scale(1.02)",
            },
          }}
        >
          <Box
            sx={{
              width: "100%",
              height: compact ? 16 : 20,
              borderRadius: 0.5,
              background: `linear-gradient(135deg, ${item.primary} 0%, ${item.background} 100%)`,
              border: 1,
              borderColor: "divider",
            }}
          />
          {!compact ? (
            <Typography variant="caption" noWrap sx={{ maxWidth: "100%", fontSize: "0.65rem" }}>
              {item.label}
            </Typography>
          ) : null}
        </Button>
      </Tooltip>
    );
  };

  return (
    <>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 1, pb: 1 }}>
        <Typography variant="subtitle2">Appearance</Typography>
        <Button
          size="small"
          variant="text"
          startIcon={<IconDice3 size={15} stroke={1.75} />}
          onClick={onSurprise}
          sx={{ textTransform: "none", fontWeight: 600 }}
        >
          Surprise me
        </Button>
      </Stack>
      <ToggleButtonGroup
        exclusive
        fullWidth
        size="small"
        value={mode}
        onChange={(_, value: "light" | "dark" | null) => {
          if (value) setMode(value);
        }}
        sx={{ mb: 2, px: 1 }}
      >
        <ToggleButton value="light">
          <IconSun size={16} stroke={1.75} style={{ marginRight: 6 }} />
          Light
        </ToggleButton>
        <ToggleButton value="dark">
          <IconMoon size={16} stroke={1.75} style={{ marginRight: 6 }} />
          Dark
        </ToggleButton>
      </ToggleButtonGroup>
      {recentSkins.length ? (
        <>
          <Typography variant="caption" color="text.secondary" sx={{ px: 1, display: "block", mb: 1 }}>
            Recent
          </Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, px: 1, mb: 1.5 }}>
            {recentSkins.map((item) => (
              <Box key={item.id}>{renderSkinButton(item, true)}</Box>
            ))}
          </Box>
        </>
      ) : null}
      <Typography variant="caption" color="text.secondary" sx={{ px: 1, display: "block", mb: 1 }}>
        Color theme · {skins.length} skins
      </Typography>
      <Box sx={{ maxHeight: 280, overflow: "auto", px: 0.5 }}>
        <Grid container spacing={1}>
          {skins.map((item) => (
            <Grid key={item.id} size={{ xs: 4 }}>
              {renderSkinButton(item)}
            </Grid>
          ))}
        </Grid>
      </Box>
    </>
  );
}

type ThemePickerMenuProps = {
  iconSize?: number;
};

export default function ThemePickerMenu({ iconSize = 18 }: ThemePickerMenuProps) {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  return (
    <>
      <Tooltip title="Theme and appearance">
        <IconButton color="inherit" size="small" onClick={(e) => setAnchorEl(e.currentTarget)} aria-label="Theme picker">
          <IconPalette size={iconSize} stroke={1.75} />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        slotProps={{ paper: { sx: themePickerMenuPaperSx } }}
      >
        <ThemeAppearanceControls onSkinSelect={() => setAnchorEl(null)} />
      </Menu>
    </>
  );
}
