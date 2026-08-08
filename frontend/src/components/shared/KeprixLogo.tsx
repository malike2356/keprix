"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { keprixTypography } from "@/theme/tokens/typography";

type KeprixLogoProps = {
  variant?: "full" | "icon";
  size?: "sm" | "md" | "lg";
  /** Force light text for fixed dark panels (marketing/auth). Default follows active theme. */
  onDark?: boolean;
};

const sizes = { sm: 24, md: 32, lg: 48 } as const;
const logoSrc = (onDark: boolean) =>
  onDark ? "/logo-mono-inv-trans.png" : "/logo-trans.png";

/** Brand mark + wordmark. Transparent crest assets (claws visible, no front disc). */
export function KeprixLogo({ variant = "full", size = "md", onDark = false }: KeprixLogoProps) {
  const px = sizes[size];
  const src = logoSrc(onDark);

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box
        aria-hidden
        component="img"
        src={src}
        alt=""
        sx={{
          width: px,
          height: px,
          objectFit: "contain",
          display: "block",
          flexShrink: 0,
          backgroundColor: "transparent",
        }}
      />
      {variant === "full" ? (
        <Typography
          variant={size === "lg" ? "h4" : size === "md" ? "h6" : "body1"}
          sx={{
            fontWeight: 600,
            letterSpacing: "-0.03em",
            fontFamily: keprixTypography.fontFamilyDisplay,
            color: onDark ? "#f5f7ff" : "text.primary",
          }}
        >
          Keprix
        </Typography>
      ) : null}
    </Box>
  );
}

export default KeprixLogo;
