"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";

type Snapshot = {
  overall: string;
  updatedAt: string;
  uptime90d: number;
  services: Array<{ id: string; name: string; health: string }>;
  openIncidents: Array<{
    id: string;
    title: string;
    phase: string;
    severity: string;
    updates: Array<{ at: string; phase: string; message: string }>;
  }>;
  upcomingMaintenance: Array<{
    title: string;
    startsAt: string;
    endsAt: string;
    description: string;
  }>;
};

export default function StatusPage() {
  const [snap, setSnap] = React.useState<Snapshot | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetch("/api/status/public")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load status");
        return res.json();
      })
      .then((data) => setSnap(data.snapshot || null))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <Box>
      <Navbar />
      <Container maxWidth="md" sx={{ pt: 12, pb: 8 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Keprix status
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Current status, incident timeline, and scheduled maintenance. This marketing page reads a
          public snapshot; health monitoring runs separately from the app containers.
        </Typography>
        {error && (
          <Typography color="error" sx={{ mb: 2 }}>
            {error}
          </Typography>
        )}
        {!snap && !error && <Typography color="text.secondary">Loading status…</Typography>}
        {snap && (
          <>
            <Typography variant="h5" sx={{ mb: 1 }}>
              {snap.overall}
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
              90-day uptime {Number(snap.uptime90d).toFixed(2)}% · Updated {snap.updatedAt}
            </Typography>
            <Typography variant="h6" sx={{ mt: 3 }}>
              Services
            </Typography>
            <Box component="ul" sx={{ pl: 2 }}>
              {snap.services.map((s) => (
                <li key={s.id}>
                  {s.name}: {s.health}
                </li>
              ))}
            </Box>
            <Typography variant="h6" sx={{ mt: 3 }}>
              Active incidents
            </Typography>
            {snap.openIncidents.length === 0 ? (
              <Typography color="text.secondary">No active incidents.</Typography>
            ) : (
              snap.openIncidents.map((i) => (
                <Box key={i.id} sx={{ mb: 2 }}>
                  <Typography fontWeight={600}>
                    {i.title} ({i.severity} · {i.phase})
                  </Typography>
                  <Box component="ol" sx={{ pl: 3 }}>
                    {i.updates.map((u, idx) => (
                      <li key={`${i.id}-${idx}`}>
                        {u.at}: {u.phase}; {u.message}
                      </li>
                    ))}
                  </Box>
                </Box>
              ))
            )}
            <Typography variant="h6" sx={{ mt: 3 }}>
              Scheduled maintenance
            </Typography>
            {snap.upcomingMaintenance.length === 0 ? (
              <Typography color="text.secondary">No upcoming maintenance windows.</Typography>
            ) : (
              <Box component="ul" sx={{ pl: 2 }}>
                {snap.upcomingMaintenance.map((m, idx) => (
                  <li key={`${m.title}-${idx}`}>
                    <strong>{m.title}</strong>: {m.startsAt} to {m.endsAt}. {m.description}
                  </li>
                ))}
              </Box>
            )}
          </>
        )}
      </Container>
      <Footer />
    </Box>
  );
}
