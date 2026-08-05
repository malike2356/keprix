"use client";

import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormHelperText from "@mui/material/FormHelperText";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { AgentAppInput } from "@/lib/agent-apps-api";

export type AgentAppFormValues = Record<string, string>;

type Props = {
  inputs: AgentAppInput[];
  values: AgentAppFormValues;
  onChange: (values: AgentAppFormValues) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
};

export function initialFormValues(inputs: AgentAppInput[] | undefined): AgentAppFormValues {
  const values: AgentAppFormValues = {};
  for (const field of inputs ?? []) {
    if (field.type === "boolean") {
      values[field.id] = String(field.default ?? false);
    } else {
      values[field.id] = String(field.default ?? "");
    }
  }
  return values;
}

export function validateAgentAppForm(
  inputs: AgentAppInput[],
  values: AgentAppFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of inputs) {
    const raw = values[field.id] ?? "";
    if (field.required && !String(raw).trim() && field.type !== "boolean") {
      errors[field.id] = `${field.label} is required`;
      continue;
    }
    if (field.type === "number" && raw.trim()) {
      const parsed = Number(raw);
      if (Number.isNaN(parsed)) {
        errors[field.id] = `${field.label} must be a number`;
      }
    }
    if (field.type === "select" && field.required && !raw.trim()) {
      errors[field.id] = `Select ${field.label.toLowerCase()}`;
    }
  }
  return errors;
}

export default function AgentAppRunForm({ inputs, values, onChange, errors = {}, disabled }: Props) {
  const setField = (id: string, value: string) => {
    onChange({ ...values, [id]: value });
  };

  if (!inputs.length) {
    return null;
  }

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {inputs.map((field) => {
        const error = errors[field.id];
        const value = values[field.id] ?? "";

        if (field.type === "boolean") {
          const checked = value === "true";
          return (
            <FormControl key={field.id} error={Boolean(error)} disabled={disabled}>
              <FormControlLabel
                control={
                  <Switch
                    checked={checked}
                    onChange={(e) => setField(field.id, e.target.checked ? "true" : "false")}
                  />
                }
                label={field.label}
              />
              {error ? <FormHelperText>{error}</FormHelperText> : null}
            </FormControl>
          );
        }

        if (field.type === "select") {
          return (
            <FormControl key={field.id} fullWidth size="small" error={Boolean(error)} disabled={disabled}>
              <InputLabel id={`${field.id}-label`}>{field.label}</InputLabel>
              <Select
                labelId={`${field.id}-label`}
                label={field.label}
                value={value}
                onChange={(e) => setField(field.id, String(e.target.value))}
              >
                {(field.options ?? []).map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
              {error ? <FormHelperText>{error}</FormHelperText> : null}
            </FormControl>
          );
        }

        if (field.type === "file") {
          return (
            <Box key={field.id}>
              <Typography variant="body2" gutterBottom>
                {field.label}
              </Typography>
              <TextField
                type="file"
                size="small"
                fullWidth
                disabled={disabled}
                inputProps={{ accept: "*/*" }}
                onChange={(e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (!file) {
                    setField(field.id, "");
                    return;
                  }
                  const reader = new FileReader();
                  reader.onload = () => {
                    const text = typeof reader.result === "string" ? reader.result : "";
                    setField(field.id, text.slice(0, 200_000));
                  };
                  reader.readAsText(file);
                }}
                helperText={error || field.placeholder || "Text files are read into the run payload"}
                error={Boolean(error)}
              />
            </Box>
          );
        }

        return (
          <TextField
            key={field.id}
            label={field.label}
            value={value}
            onChange={(e) => setField(field.id, e.target.value)}
            required={field.required}
            placeholder={field.placeholder}
            multiline={field.type === "textarea"}
            minRows={field.type === "textarea" ? 3 : undefined}
            type={field.type === "number" ? "number" : "text"}
            size="small"
            fullWidth
            disabled={disabled}
            error={Boolean(error)}
            helperText={error}
          />
        );
      })}
    </Box>
  );
}
