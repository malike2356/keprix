"use client";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import PageHeader from "@/components/ui/PageHeader";
import FeatureCard from "@/components/ui/FeatureCard";
import { launcherCards } from "@/lib/navigation";

export default function LauncherPage() {
  return (
    <Box>
      <PageHeader
        title="Home"
        description="Choose a capability to open your workspace tools."
        breadcrumbs={[{ label: "Workspace", href: "/launcher" }, { label: "Home" }]}
      />
      <Grid container spacing={2}>
        {launcherCards.map((card) => (
          <Grid key={card.id} size={{ xs: 12, sm: 6, lg: 4, xl: 3 }}>
            <FeatureCard
              title={card.title}
              description={card.description}
              href={card.href}
              icon={card.icon}
            />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
