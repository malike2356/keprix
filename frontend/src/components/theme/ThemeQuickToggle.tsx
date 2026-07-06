"use client";

import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import { IconMoon, IconSun } from "@tabler/icons-react";
import * as React from "react";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

type ThemeQuickToggleProps = {
  size?: "small" | "medium";
  color?: "inherit" | "default";
};

export default function ThemeQuickToggle({ size = "small", color = "inherit" }: ThemeQuickToggleProps) {
  const { mode, toggleMode } = useThemeMode();
  const isLight = mode === "light";

  return (
    <Tooltip title={isLight ? "Switch to dark mode" : "Switch to light mode"}>
      <IconButton
        color={color}
        size={size}
        onClick={toggleMode}
        aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
        className="keprix-theme-toggle"
        sx={{
          transition: "transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
          "&:active": { transform: "scale(0.9)" },
          "& .keprix-theme-toggle-icon": {
            display: "inline-flex",
            transition: "transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease",
            transform: isLight ? "rotate(-24deg) scale(1.05)" : "rotate(0deg) scale(1)",
          },
        }}
      >
        <span key={mode} className="keprix-theme-toggle-icon">
          {isLight ? <IconMoon size={18} stroke={1.75} /> : <IconSun size={18} stroke={1.75} />}
        </span>
      </IconButton>
    </Tooltip>
  );
}
