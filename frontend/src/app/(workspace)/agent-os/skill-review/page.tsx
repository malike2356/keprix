"use client";

import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Report = {
  generated_at: string;
  pending: Array<{ proposal_id: string; name: string; source: string }>;
  approved: Array<{ proposal_id: string; name: string; source: string }>;
  rejected: Array<{ proposal_id: string; name: string; source: string }>;
};

export default function SkillReviewPage() {
  const [report, setReport] = React.useState<Report | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  const load = React.useCallback(async (generate = false) => {
    const response = await ceApi(generate ? "/api/agent-os/skill-review/generate" : "/api/agent-os/skill-review/latest", {
      method: generate ? "POST" : "GET",
    });
    if (!response.ok) {
      setMessage("Failed to load review report.");
      return;
    }
    const payload = (await response.json()) as { report: Report };
    setReport(payload.report);
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const rows = [
    { label: "Pending", items: report?.pending || [] },
    { label: "Approved", items: report?.approved || [] },
    { label: "Rejected", items: report?.rejected || [] },
  ];

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Skill review"
        description="Weekly review of skill proposals and packaged workflow skills."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Skill review" },
        ]}
      />
      <Button sx={{ width: "fit-content" }} startIcon={<RefreshIcon />} onClick={() => void load(true)}>
        Generate report
      </Button>
      {report && <Typography variant="body2" color="text.secondary">Generated {new Date(report.generated_at).toLocaleString()}</Typography>}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Status</TableCell>
            <TableCell>Count</TableCell>
            <TableCell>Latest items</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.label}>
              <TableCell>{row.label}</TableCell>
              <TableCell>{row.items.length}</TableCell>
              <TableCell>{row.items.slice(0, 3).map((item) => item.name).join(", ") || "None"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}
