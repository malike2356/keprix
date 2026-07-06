"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function TypingIndicator() {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: { xs: 1, md: 3 }, py: 1 }}>
      <Typography variant="body2" color="text.secondary">
        keprix is thinking
      </Typography>
      <Box sx={{ display: "flex", gap: 0.5 }}>
        {[0, 1, 2].map((index) => (
          <Box
            key={index}
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "text.secondary",
              opacity: 0.5 + index * 0.15,
              animation: "pulse 1.2s ease-in-out infinite",
              animationDelay: `${index * 0.15}s`,
              "@keyframes pulse": {
                "0%, 100%": { transform: "translateY(0)" },
                "50%": { transform: "translateY(-3px)" },
              },
            }}
          />
        ))}
      </Box>
    </Box>
  );
}
