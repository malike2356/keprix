"use client";

import Box from "@mui/material/Box";

type KeprixWordmarkProps = {
  size?: "md" | "lg" | "hero";
  onDark?: boolean;
};

const sizes = {
  md: { width: 120, height: 120 },
  lg: { width: 170, height: 170 },
  hero: { width: 240, height: 240 },
} as const;

const logoSrc = (onDark: boolean) =>
  onDark ? "/logo-mono-inv-trans.png" : "/logo-trans.png";

export default function KeprixWordmark({ size = "lg", onDark = true }: KeprixWordmarkProps) {
  const dim = sizes[size];

  return (
    <Box
      component="img"
      src={logoSrc(onDark)}
      alt="Keprix"
      sx={{
        width: dim.width,
        height: dim.height,
        objectFit: "contain",
        display: "block",
        backgroundColor: "transparent",
      }}
    />
  );
}
