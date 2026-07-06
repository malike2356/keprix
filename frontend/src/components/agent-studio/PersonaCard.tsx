"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { Persona } from "@/lib/personas-api";

type PersonaCardProps = {
  persona: Persona;
  selected?: boolean;
  onSelect?: (persona: Persona) => void;
};

export default function PersonaCard({ persona, selected = false, onSelect }: PersonaCardProps) {
  return (
    <Card
      variant={selected ? "elevation" : "outlined"}
      sx={{
        borderColor: selected ? persona.colour : undefined,
        borderWidth: selected ? 2 : 1,
        cursor: onSelect ? "pointer" : "default",
      }}
      onClick={() => onSelect?.(persona)}
    >
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              bgcolor: persona.colour,
              flexShrink: 0,
            }}
          />
          <Typography variant="h6" component="span">
            {persona.name}
          </Typography>
          <Chip size="small" label={persona.agent_type} />
        </Box>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {persona.role}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {persona.tone}
        </Typography>
        {persona.skill_packs.length > 0 ? (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1.5 }}>
            {persona.skill_packs.map((pack) => (
              <Chip key={pack} size="small" variant="outlined" label={pack} />
            ))}
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
