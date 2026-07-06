"use client";

import * as React from "react";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { useSearchParams } from "next/navigation";
import AdminTable from "@/components/admin/AdminTable";
import MutationReviewDrawer from "@/components/admin/MutationReviewDrawer";
import PageContainer from "@/components/shared/PageContainer";
import { useRequireAdmin } from "@/lib/ce-auth";
import { fetchGeneratedToolMutations, type GeneratedToolMutation } from "@/lib/admin-pages-api";
import { fetchMutationStats } from "@/lib/mutation-api";

type StatusTab = "all" | "staged" | "approved" | "rejected";

function normalizeStatus(status: string): string {
  if (status === "pending" || status === "pending_approval") return "staged";
  return status;
}

function matchesTab(row: GeneratedToolMutation, tab: StatusTab): boolean {
  const status = normalizeStatus(row.status);
  if (tab === "all") return true;
  if (tab === "staged") return status === "staged";
  return status === tab;
}

export default function AdminMutationsPage() {
  useRequireAdmin();
  const searchParams = useSearchParams();
  const { data: stats } = useSWR("mutation-stats", fetchMutationStats);
  const stagedCount = stats?.staged ?? 0;
  const statusParam = searchParams.get("status");

  const [tab, setTab] = React.useState<StatusTab>(() => {
    if (statusParam === "staged") return "staged";
    return stagedCount > 0 ? "staged" : "all";
  });
  const [reviewTarget, setReviewTarget] = React.useState<GeneratedToolMutation | null>(null);

  React.useEffect(() => {
    if (statusParam === "staged") {
      setTab("staged");
      return;
    }
    if (stagedCount > 0) setTab("staged");
  }, [stagedCount, statusParam]);

  const { data, isLoading, mutate } = useSWR("admin-mutations-review", () => fetchGeneratedToolMutations(50));

  const rows = (data || [])
    .filter((row) => matchesTab(row, tab))
    .map((row) => ({
      ...row,
      id: row.id,
      status: normalizeStatus(row.status),
    }));

  const columns = [
    { id: "tool_name", label: "Tool name" },
    {
      id: "status",
      label: "Status",
      render: (row: GeneratedToolMutation & { status: string }) => (
        <Chip
          size="small"
          label={row.status}
          color={row.status === "approved" ? "success" : row.status === "rejected" ? "error" : "warning"}
          variant="outlined"
        />
      ),
    },
    {
      id: "workspace_id",
      label: "Workspace",
      render: () => "default",
    },
    {
      id: "requested_at",
      label: "Created",
      render: (row: GeneratedToolMutation) =>
        row.requested_at ? new Date(row.requested_at).toLocaleDateString() : "—",
    },
    {
      id: "actions",
      label: "Actions",
      render: (row: GeneratedToolMutation & { status: string }) => (
        <Button
          size="small"
          variant={row.status === "staged" ? "outlined" : "text"}
          onClick={(e) => {
            e.stopPropagation();
            setReviewTarget(row);
          }}
        >
          {row.status === "staged" ? "Review" : "View"}
        </Button>
      ),
    },
  ];

  return (
    <PageContainer
      title="Mutation review"
      description="Review synthesised tools before they enter the active library."
      padded={false}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Tabs value={tab} onChange={(_, value: StatusTab) => setTab(value)}>
          <Tab label="All" value="all" />
          <Tab
            label={
              <Badge badgeContent={stagedCount} color="warning" invisible={stagedCount === 0}>
                <Typography component="span" variant="body2" sx={{ pr: stagedCount > 0 ? 2 : 0 }}>
                  Staged
                </Typography>
              </Badge>
            }
            value="staged"
          />
          <Tab label="Approved" value="approved" />
          <Tab label="Rejected" value="rejected" />
        </Tabs>

        <AdminTable
          columns={columns}
          rows={rows}
          loading={isLoading}
          onRowClick={(row) => setReviewTarget(row)}
        />

        <Typography variant="caption" color="text.secondary">
          Full governance controls remain on{" "}
          <a href="/dashboard/mutation">/dashboard/mutation</a>.
        </Typography>
      </Box>

      <MutationReviewDrawer
        mutationId={reviewTarget?.id ?? null}
        toolName={reviewTarget?.tool_name || "Mutation"}
        status={reviewTarget ? normalizeStatus(reviewTarget.status) : "staged"}
        open={Boolean(reviewTarget)}
        onClose={() => setReviewTarget(null)}
        onResolved={() => void mutate()}
      />
    </PageContainer>
  );
}
