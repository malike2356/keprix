"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

type KeprixWordmarkProps = {
  size?: "md" | "lg" | "hero";
};

const sizes = {
  md: { fontSize: "1.75rem", letterSpacing: "-0.03em" },
  lg: { fontSize: "2.75rem", letterSpacing: "-0.04em" },
  hero: { fontSize: "4.5rem", letterSpacing: "-0.05em" },
} as const;

export default function KeprixWordmark({ size = "lg" }: KeprixWordmarkProps) {
  const style = sizes[size];
  return (
    <Box sx={{ textAlign: "center" }}>
      <Typography
        component="div"
        sx={{
          fontWeight: 900,
          lineHeight: 1,
          background: "linear-gradient(135deg, #6c5ce7 0%, #6495ed 55%, #8e44ad 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          ...style,
        }}
      >
        keprix
      </Typography>
    </Box>
  );
}
