"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FilterListIcon from "@mui/icons-material/FilterList";
import * as React from "react";

type FilterBarProps = {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  filters?: Array<{ id: string; label: string; active?: boolean; onClick: () => void }>;
  actions?: React.ReactNode;
};

export default function FilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = "Search records",
  filters = [],
  actions,
}: FilterBarProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: { xs: "column", md: "row" },
        gap: 2,
        alignItems: { md: "center" },
        mb: 2,
      }}
    >
      <TextField
        size="small"
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={searchPlaceholder}
        sx={{ minWidth: { md: 240 }, flex: 1 }}
      />
      {filters.length > 0 && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
          <FilterListIcon fontSize="small" color="action" />
          {filters.map((filter) => (
            <Chip
              key={filter.id}
              label={filter.label}
              size="small"
              color={filter.active ? "primary" : "default"}
              variant={filter.active ? "filled" : "outlined"}
              onClick={filter.onClick}
            />
          ))}
        </Box>
      )}
      {actions && <Box sx={{ ml: { md: "auto" } }}>{actions}</Box>}
      {filters.length === 0 && !actions && (
        <Typography variant="caption" color="text.secondary">
          Use search to narrow results.
        </Typography>
      )}
    </Box>
  );
}
