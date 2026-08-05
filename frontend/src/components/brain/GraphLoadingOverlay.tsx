"use client";

import Box from "@mui/material/Box";

export default function GraphLoadingOverlay() {
  const nodes = Array.from({ length: 10 }, (_, index) => index);
  return (
    <Box sx={{ position: "absolute", inset: 0, bgcolor: "background.default", overflow: "hidden", zIndex: 5 }}>
      {nodes.map((index) => (
        <Box
          key={index}
          sx={{
            position: "absolute",
            left: `${12 + (index % 5) * 18}%`,
            top: `${18 + Math.floor(index / 5) * 36 + (index % 2) * 6}%`,
            width: 36 + (index % 4) * 10,
            height: 36 + (index % 4) * 10,
            borderRadius: "50%",
            bgcolor: "action.hover",
            animation: "pulse 1.4s ease-in-out infinite",
            "@keyframes pulse": {
              "0%, 100%": { opacity: 0.35 },
              "50%": { opacity: 0.75 },
            },
          }}
        />
      ))}
    </Box>
  );
}
