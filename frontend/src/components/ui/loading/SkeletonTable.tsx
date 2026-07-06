"use client";

import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";

type SkeletonTableProps = {
  rows?: number;
  columns?: number;
};

export default function SkeletonTable({ rows = 6, columns = 4 }: SkeletonTableProps) {
  return (
    <TableContainer component={Paper} variant="outlined" data-testid="skeleton-table">
      <Table size="small">
        <TableHead>
          <TableRow>
            {Array.from({ length: columns }).map((_, index) => (
              <TableCell key={index}>
                <SkeletonBlock height={16} width={`${55 + (index % 3) * 10}%`} />
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <TableRow key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <TableCell key={colIndex}>
                  <SkeletonBlock height={14} width={colIndex === 0 ? "88%" : "70%"} />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
