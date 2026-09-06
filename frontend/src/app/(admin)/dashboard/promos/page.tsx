"use client";

import Alert from "@mui/material/Alert";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import PageContainer from "@/components/shared/PageContainer";
import { useRequireAdmin } from "@/lib/ce-auth";
import { fetchPromoRedemptions } from "@/lib/admin-promo-api";

export default function PromoRedemptionsPage() {
  useRequireAdmin();
  const { data, error } = useSWR("admin-promo-redemptions", fetchPromoRedemptions);
  return (
    <PageContainer title="Promo redemptions" description="Confirmed Stripe redemptions with redacted code identifiers." padded={false}>
      <Stack spacing={2}>
        {error ? <Alert severity="error">{error.message}</Alert> : null}
        <Typography variant="body2">Total confirmed redemptions: {data?.count ?? 0}</Typography>
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead><TableRow><TableCell>Code</TableCell><TableCell>Workspace</TableCell><TableCell>Order</TableCell><TableCell>Redeemed</TableCell></TableRow></TableHead>
            <TableBody>{(data?.items || []).map((row) => <TableRow key={row.order_id}><TableCell>{row.code}</TableCell><TableCell>{row.workspace_id}</TableCell><TableCell>{row.order_id}</TableCell><TableCell>{row.redeemed_at}</TableCell></TableRow>)}</TableBody>
          </Table>
        </Paper>
      </Stack>
    </PageContainer>
  );
}
