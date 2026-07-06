"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";

type KeprixLogoProps = {
  variant?: "full" | "icon";
  size?: "sm" | "md" | "lg";
  /** Force light text for fixed dark panels (marketing/auth). Default follows active theme. */
  onDark?: boolean;
};

const sizes = { sm: 24, md: 32, lg: 48 } as const;

export function KeprixLogo({ variant = "full", size = "md", onDark = false }: KeprixLogoProps) {
  const px = sizes[size];

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box
        aria-hidden
        sx={{
          width: px,
          height: px,
          borderRadius: "50%",
          bgcolor: KEPRIX_COLORS.primary,
          border: `1px solid ${KEPRIX_COLORS.divider}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: px * 0.45,
          color: "#fff",
          fontWeight: 700,
        }}
      >
        K
      </Box>
      {variant === "full" ? (
        <Typography
          variant={size === "lg" ? "h4" : size === "md" ? "h6" : "body1"}
          sx={{
            fontWeight: 800,
            letterSpacing: "-0.02em",
            color: onDark ? KEPRIX_COLORS.textPrimary : "text.primary",
          }}
        >
          Keprix
        </Typography>
      ) : null}
    </Box>
  );
}

export default KeprixLogo;
