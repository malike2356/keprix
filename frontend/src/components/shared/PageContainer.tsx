"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import BlankCard from "@/components/cards/BlankCard";

type PageContainerProps = {
  title?: string;
  description?: string;
  children: ReactNode;
  padded?: boolean;
};

export default function PageContainer({ title, description, children, padded = true }: PageContainerProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {(title || description) && (
        <Box>
          {title ? (
            <Typography variant="h4" component="h1" sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
              {title}
            </Typography>
          ) : null}
          {description ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          ) : null}
        </Box>
      )}
      {padded ? (
        <BlankCard>
          <Box sx={{ p: { xs: 2, md: 3 } }}>{children}</Box>
        </BlankCard>
      ) : (
        children
      )}
    </Box>
  );
}
