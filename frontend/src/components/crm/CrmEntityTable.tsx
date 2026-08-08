"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import {
  companyLabel,
  displayName,
  formatTouch,
  primaryEmail,
  stageLabel,
  type CrmRecord,
} from "@/components/crm/types";

type CrmEntityTableProps = {
  rows: CrmRecord[];
  hrefFor: (row: CrmRecord) => string;
  selectedIds?: Set<string>;
  onToggle?: (id: string) => void;
  onToggleAll?: () => void;
  emptyMessage?: string;
  showCompanyAsName?: boolean;
};

export function CrmEntityTable({
  rows,
  hrefFor,
  selectedIds,
  onToggle,
  onToggleAll,
  emptyMessage = "No records yet. Import or create items to populate this list.",
  showCompanyAsName = false,
}: CrmEntityTableProps) {
  if (rows.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        {emptyMessage}
      </Typography>
    );
  }

  const allSelected = selectedIds ? rows.every((row) => selectedIds.has(row.id)) : false;

  return (
    <TableContainer sx={{ width: "100%", overflowX: "auto" }}>
      <Table size="small" sx={{ minWidth: 720 }}>
        <TableHead>
          <TableRow>
            {selectedIds && onToggle ? (
              <TableCell padding="checkbox">
                <Checkbox
                  size="small"
                  checked={allSelected}
                  indeterminate={!allSelected && selectedIds.size > 0}
                  onChange={onToggleAll}
                  inputProps={{ "aria-label": "Select all rows" }}
                />
              </TableCell>
            ) : null}
            <TableCell>Name</TableCell>
            <TableCell>Stage</TableCell>
            <TableCell>Source</TableCell>
            <TableCell>Company</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Last touch</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => {
            const company = showCompanyAsName ? displayName(row) : companyLabel(row);
            return (
              <TableRow key={row.id} hover selected={selectedIds?.has(row.id)}>
                {selectedIds && onToggle ? (
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={selectedIds.has(row.id)}
                      onChange={() => onToggle(row.id)}
                      inputProps={{ "aria-label": `Select ${displayName(row)}` }}
                    />
                  </TableCell>
                ) : null}
                <TableCell>
                  <Typography
                    component={Link}
                    href={hrefFor(row)}
                    variant="body2"
                    fontWeight={600}
                    sx={{ color: "primary.main", textDecoration: "none" }}
                  >
                    {displayName(row)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={stageLabel(row.stage || row.status)} variant="outlined" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {row.source || "-"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {company || "-"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {primaryEmail(row) || "-"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary" noWrap>
                    {formatTouch(row.last_touch_at)}
                  </Typography>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      {selectedIds && selectedIds.size > 0 ? (
        <Box sx={{ mt: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" color="text.secondary">
              {selectedIds.size} selected
            </Typography>
            <Button size="small" disabled>
              Bulk actions use the toolbar above
            </Button>
          </Stack>
        </Box>
      ) : null}
    </TableContainer>
  );
}

export default CrmEntityTable;
