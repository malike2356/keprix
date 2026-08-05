"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  listStudioTemplates,
  loadStudioTemplate,
  type StudioTemplate,
} from "@/lib/playbook-studio/playbook-studio-api";
import type { StudioCanvas } from "@/lib/playbook-studio/canvas-types";

export default function TemplatesPanel({ onUse }: { onUse: (canvas: StudioCanvas) => void }) {
  const [query, setQuery] = React.useState("");
  const { data = [] } = useSWR("studio-templates", listStudioTemplates);
  const templates = data.filter((template) =>
    `${template.title} ${template.description}`.toLowerCase().includes(query.toLowerCase()),
  );

  const useTemplate = async (template: StudioTemplate) => {
    const payload = await loadStudioTemplate(template.id);
    onUse(payload.canvas);
  };

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Templates</Typography>
      <TextField size="small" label="Search" value={query} onChange={(event) => setQuery(event.target.value)} />
      {templates.map((template) => (
        <Box key={template.id} sx={{ display: "grid", gap: 0.5 }}>
          <Typography variant="body2" fontWeight={600}>
            {template.title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {template.description}
          </Typography>
          <Button size="small" onClick={() => void useTemplate(template)}>
            Use template
          </Button>
        </Box>
      ))}
    </Box>
  );
}
