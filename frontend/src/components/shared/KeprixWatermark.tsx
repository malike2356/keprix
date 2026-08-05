"use client";

import Box from "@mui/material/Box";

type KeprixWatermarkProps = {
  /** Extra sx merged onto the outer absolute layer. */
  sx?: object;
  /** Crest size as a CSS length; default scales with viewport. */
  size?: string;
  /** Opacity of the watermark layer. */
  opacity?: number;
};

/**
 * Subtle transparent crest for empty canvases, auth panels, and mobile shells.
 * Uses `/logo-trans.png` (claws visible, no front disc).
 */
export default function KeprixWatermark({
  sx,
  size = "min(72vmin, 520px)",
  opacity = 0.06,
}: KeprixWatermarkProps) {
  return (
    <Box
      aria-hidden
      sx={{
        pointerEvents: "none",
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        zIndex: 0,
        ...sx,
      }}
    >
      <Box
        component="img"
        src="/logo-trans.png"
        alt=""
        sx={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: size,
          height: size,
          maxWidth: "none",
          objectFit: "contain",
          opacity,
          transform: "translate(-46%, -42%)",
          userSelect: "none",
          mixBlendMode: "soft-light",
        }}
      />
    </Box>
  );
}
