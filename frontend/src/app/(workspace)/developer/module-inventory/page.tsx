"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import PageHeader from "@/components/ui/PageHeader";
import { fetchModuleInventory } from "@/lib/developer-api";

export default function ModuleInventoryPage() {
  const { data, error, isLoading } = useSWR("module-inventory", fetchModuleInventory, {
    revalidateOnFocus: false,
  });

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Module inventory"
        description="Compare built workspace pages and backend API modules against the main navigation contract."
        breadcrumbs={[
          { label: "Developer", href: "/developer" },
          { label: "Module inventory" },
        ]}
      />

      {error ? <Alert severity="error">{error instanceof Error ? error.message : "Failed to load inventory"}</Alert> : null}

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Chip label={`Navigation links ${data?.navigation_count ?? "-"}`} />
        <Chip label={`Workspace pages ${data?.workspace_page_count ?? "-"}`} />
        <Chip color={(data?.unlinked_workspace_page_count ?? 0) > 0 ? "warning" : "success"} label={`Unlinked pages ${data?.unlinked_workspace_page_count ?? "-"}`} />
        <Chip label={`API modules ${data?.api_module_count ?? "-"}`} />
      </Box>

      <DashboardCard title="Built pages not in main navigation" subtitle="Static workspace routes that exist but are not linked from the app shell.">
        {isLoading ? <Typography color="text.secondary">Loading...</Typography> : null}
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Route</TableCell>
              <TableCell>File</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.unlinked_workspace_pages || []).map((page) => (
              <TableRow key={page.file}>
                <TableCell>{page.route}</TableCell>
                <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{page.file}</TableCell>
              </TableRow>
            ))}
            {data && data.unlinked_workspace_pages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography color="text.secondary">Every static workspace page is represented in navigation.</Typography>
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </DashboardCard>

      <DashboardCard title="Backend API modules" subtitle="Registered API route modules discovered in src/keprix/api.">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Module</TableCell>
              <TableCell>Routes</TableCell>
              <TableCell>File</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.api_modules || []).map((module) => (
              <TableRow key={module.file}>
                <TableCell>{module.module}</TableCell>
                <TableCell>{module.route_count}</TableCell>
                <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{module.file}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DashboardCard>
    </Box>
  );
}
