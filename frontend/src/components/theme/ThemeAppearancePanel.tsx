"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Menu from "@mui/material/Menu";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { IconDice3, IconPalette } from "@tabler/icons-react";
import * as React from "react";
import { useThemeMode } from "@/components/providers/ThemeRegistry";
import { ThemeAppearanceControls, themePickerMenuPaperSx } from "@/components/theme/ThemePickerMenu";
import { pickRandomSkinId } from "@/theme/theme-recent";

export default function ThemeAppearancePanel() {
  const { mode, skin, skins, setSkin } = useThemeMode();
  const activeSkin = skins.find((item) => item.id === skin);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          py: 1.5,
          "&:last-child": { pb: 1.5 },
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ minWidth: 0 }}>
          {activeSkin ? (
            <Box
              sx={{
                width: 40,
                height: 28,
                flexShrink: 0,
                borderRadius: 1,
                background: `linear-gradient(135deg, ${activeSkin.primary} 0%, ${activeSkin.background} 100%)`,
                border: 1,
                borderColor: "divider",
                transition: "transform 0.25s ease",
              }}
            />
          ) : null}
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2">Appearance</Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              {activeSkin?.label ?? skin} · {mode === "dark" ? "Dark" : "Light"} · {skins.length} skins
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ flexShrink: 0 }}>
          <Button
            size="small"
            variant="text"
            startIcon={<IconDice3 size={16} stroke={1.75} />}
            onClick={() => setSkin(pickRandomSkinId(skin, skins))}
            sx={{ textTransform: "none" }}
          >
            Surprise me
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<IconPalette size={16} stroke={1.75} />}
            onClick={(e) => setAnchorEl(e.currentTarget)}
          >
            Change
          </Button>
        </Stack>
      </CardContent>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        slotProps={{ paper: { sx: themePickerMenuPaperSx } }}
      >
        <ThemeAppearanceControls onSkinSelect={() => setAnchorEl(null)} />
      </Menu>
    </Card>
  );
}
