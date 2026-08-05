"use client";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { StudioVariable } from "@/lib/playbook-studio/canvas-types";

export default function VariablesPanel({
  variables,
  onChange,
}: {
  variables: StudioVariable[];
  onChange: (variables: StudioVariable[]) => void;
}) {
  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="subtitle2">Variables</Typography>
        <IconButton
          size="small"
          onClick={() => onChange([...variables, { name: "new_variable", type: "string", default: "" }])}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Box>
      {variables.map((variable, index) => (
        <Box key={`${variable.name}-${index}`} sx={{ display: "grid", gap: 1 }}>
          <TextField
            size="small"
            label="Name"
            value={variable.name}
            onChange={(event) => {
              const next = [...variables];
              next[index] = { ...variable, name: event.target.value };
              onChange(next);
            }}
          />
          <TextField
            select
            size="small"
            label="Type"
            value={variable.type}
            onChange={(event) => {
              const next = [...variables];
              next[index] = { ...variable, type: event.target.value as StudioVariable["type"] };
              onChange(next);
            }}
          >
            {["string", "number", "boolean"].map((type) => (
              <MenuItem key={type} value={type}>
                {type}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Default"
            value={String(variable.default ?? "")}
            onChange={(event) => {
              const next = [...variables];
              next[index] = { ...variable, default: event.target.value };
              onChange(next);
            }}
          />
          <TextField
            size="small"
            label="Description"
            value={variable.description || ""}
            onChange={(event) => {
              const next = [...variables];
              next[index] = { ...variable, description: event.target.value };
              onChange(next);
            }}
          />
          <IconButton size="small" onClick={() => onChange(variables.filter((_, itemIndex) => itemIndex !== index))}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ))}
      {!variables.length ? (
        <Typography variant="body2" color="text.secondary">
          Add variables to use state refs in prompts.
        </Typography>
      ) : null}
    </Box>
  );
}
