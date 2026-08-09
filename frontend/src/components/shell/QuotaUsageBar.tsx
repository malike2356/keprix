"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import { alpha, useTheme } from "@mui/material/styles";
import useSWR from "swr";
import { ceApi } from "@/lib/ce-api";

type QuotaUsagePayload = {
  usages?: Array<{
    product_id: string;
    usage?: Record<string, number>;
    limits?: Record<string, number>;
  }>;
};

async function fetchQuotaUsage() {
  const response = await ceApi("/api/admin/quotas");
  if (!response.ok) return null;
  return (await response.json()) as QuotaUsagePayload;
}

function highestTokenUsage(payload: QuotaUsagePayload | null | undefined) {
  let best: { productId: string; pct: number; used: number; limit: number } | null = null;
  for (const item of payload?.usages ?? []) {
    const used = item.usage?.llm_tokens_in ?? 0;
    const limit = item.limits?.llm_tokens_in ?? 0;
    if (limit <= 0) continue;
    const pct = used / limit;
    if (!best || pct > best.pct) best = { productId: item.product_id, pct, used, limit };
  }
  return best;
}

export default function QuotaUsageBar() {
  const theme = useTheme();
  const { data } = useSWR("nav-quota-usage", fetchQuotaUsage, {
    refreshInterval: 120_000,
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });
  const quota = highestTokenUsage(data);
  if (!quota || quota.pct < 0.7) return null;
  const value = Math.min(100, Math.round(quota.pct * 100));
  const tone = value >= 90 ? theme.palette.error.main : theme.palette.warning.main;
  return (
    <Box
      component="a"
      href="/admin/quotas"
      sx={{
        display: "block",
        mx: 1.5,
        mb: 1,
        p: 1,
        borderRadius: 1,
        textDecoration: "none",
        color: "text.primary",
        bgcolor: alpha(tone, theme.palette.mode === "dark" ? 0.18 : 0.12),
        border: "1px solid",
        borderColor: alpha(tone, 0.45),
      }}
    >
      <Typography variant="caption" sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
        <span>{quota.productId} quota</span>
        <span>{value}%</span>
      </Typography>
      <LinearProgress
        variant="determinate"
        value={value}
        color={value >= 90 ? "error" : "warning"}
        sx={{ mt: 0.75, height: 5, borderRadius: 1 }}
      />
    </Box>
  );
}
