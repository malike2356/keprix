"use client";

import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import {
  USAGE_PERIOD_OPTIONS,
  storeUsagePeriod,
  type UsagePeriodDays,
} from "@/lib/usage-api";

type UsagePeriodToolbarProps = {
  value: UsagePeriodDays;
  onChange: (days: UsagePeriodDays) => void;
};

export default function UsagePeriodToolbar({ value, onChange }: UsagePeriodToolbarProps) {
  const handleSelect = (days: UsagePeriodDays) => {
    storeUsagePeriod(days);
    onChange(days);
  };

  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 3, flexWrap: "wrap" }}>
      <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
        Period
      </Typography>
      {USAGE_PERIOD_OPTIONS.map((days) => (
        <Chip
          key={days}
          label={`${days}d`}
          clickable
          color={value === days ? "primary" : "default"}
          variant={value === days ? "filled" : "outlined"}
          onClick={() => handleSelect(days)}
          aria-pressed={value === days}
        />
      ))}
    </Stack>
  );
}
