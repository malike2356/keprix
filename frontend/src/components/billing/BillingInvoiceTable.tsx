"use client";

import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonTable } from "@/components/ui/loading";
import type { BillingInvoice } from "@/lib/billing-api";
import { formatBillingDate, formatMoneyMinorUnits } from "@/lib/billing-format";

type BillingInvoiceTableProps = {
  invoices: BillingInvoice[];
  loading?: boolean;
  onViewInvoice: (invoiceId: string) => void;
};

export default function BillingInvoiceTable({ invoices, loading, onViewInvoice }: BillingInvoiceTableProps) {
  return (
    <DashboardCard title="Invoices" subtitle="Billing history for your account">
      {loading ? (
        <SkeletonTable rows={5} columns={5} />
      ) : invoices.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No invoices yet. Invoices appear after your first successful payment.
        </Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Number</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Total</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>{formatBillingDate(invoice.created_at)}</TableCell>
                  <TableCell>{invoice.number || invoice.id}</TableCell>
                  <TableCell>{invoice.status || "-"}</TableCell>
                  <TableCell align="right">
                    {invoice.total !== undefined
                      ? formatMoneyMinorUnits(invoice.total, invoice.currency || "gbp")
                      : "-"}
                  </TableCell>
                  <TableCell align="right">
                    {invoice.html_body || invoice.pdf_url ? (
                      <Button size="small" onClick={() => onViewInvoice(invoice.id)}>
                        View
                      </Button>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DashboardCard>
  );
}
