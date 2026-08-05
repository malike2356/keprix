"use client";

import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import type { ConnectorCategory } from "@/lib/integrations-api";

export default function CategoryFilter({
  categories,
  value,
  onChange,
}: {
  categories: ConnectorCategory[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
      <Chip label="All" color={value === "all" ? "primary" : "default"} onClick={() => onChange("all")} />
      {categories.map((category) => (
        <Chip
          key={category.id}
          label={`${category.label} ${category.count}`}
          color={value === category.id ? "primary" : "default"}
          onClick={() => onChange(category.id)}
        />
      ))}
    </Stack>
  );
}
