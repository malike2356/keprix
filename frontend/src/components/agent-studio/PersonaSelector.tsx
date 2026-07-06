"use client";

import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import PersonaCard from "@/components/agent-studio/PersonaCard";
import { SkeletonBlock } from "@/components/ui/loading";
import { fetchPersonas, type Persona } from "@/lib/personas-api";

type PersonaSelectorProps = {
  value?: string;
  onChange?: (persona: Persona | null) => void;
  layout?: "grid" | "select";
};

export default function PersonaSelector({ value, onChange, layout = "grid" }: PersonaSelectorProps) {
  const { data, isLoading, error } = useSWR("personas", fetchPersonas);
  const personas = data?.personas ?? [];
  const selected = personas.find((persona) => persona.name === value) ?? null;

  if (isLoading) {
    if (layout === "select") {
      return <SkeletonBlock height={40} />;
    }
    return (
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
        }}
      >
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} height={140} />
        ))}
      </Box>
    );
  }

  if (error) {
    return <Typography variant="body2" color="error">Failed to load personas.</Typography>;
  }

  if (layout === "select") {
    return (
      <FormControl fullWidth size="small">
        <InputLabel id="persona-selector-label">Persona</InputLabel>
        <Select
          labelId="persona-selector-label"
          label="Persona"
          value={value ?? ""}
          onChange={(event) => {
            const next = personas.find((persona) => persona.name === event.target.value) ?? null;
            onChange?.(next);
          }}
        >
          {personas.map((persona) => (
            <MenuItem key={persona.name} value={persona.name}>
              {persona.name} - {persona.role}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gap: 2,
        gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
      }}
    >
      {personas.map((persona) => (
        <PersonaCard
          key={persona.name}
          persona={persona}
          selected={selected?.name === persona.name}
          onSelect={(next) => onChange?.(next)}
        />
      ))}
    </Box>
  );
}
