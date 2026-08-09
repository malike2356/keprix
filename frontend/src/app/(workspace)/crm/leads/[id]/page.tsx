"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import useSWR from "swr";
import CrmDetailEditor from "@/components/crm/CrmDetailEditor";
import CrmSoftLockBanner from "@/components/crm/CrmSoftLockBanner";
import { CRM_WORKSPACE, type CrmRecord } from "@/components/crm/types";
import { fetchCrmRecord } from "@/lib/crm-api";

export default function CrmLeadDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detail = useSWR(id ? ["crm-lead", CRM_WORKSPACE, id] : null, () =>
    fetchCrmRecord("leads", id, CRM_WORKSPACE),
  );

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading lead...</Typography>;
  }

  const record = detail.data?.record as CrmRecord | undefined;
  if (!record) {
    return (
      <Typography color="text.secondary">
        Lead not found.{" "}
        <Typography component="a" href="/crm/leads" color="primary" sx={{ textDecoration: "underline" }}>
          Back to leads
        </Typography>
      </Typography>
    );
  }

  return (
    <Box>
      <CrmSoftLockBanner entityType="lead" entityId={record.id} />
      <CrmDetailEditor
        kind="leads"
        record={record}
        backHref="/crm/leads"
        backLabel="All leads"
        onSaved={() => void detail.mutate()}
        fields={[
          { key: "name", label: "Name" },
          { key: "email", label: "Email" },
          { key: "company_name", label: "Company" },
          { key: "company_number", label: "Company number" },
          { key: "source", label: "Source" },
          { key: "assigned_agent", label: "Assigned agent" },
          { key: "tags", label: "Tags (comma separated)" },
        ]}
      />
    </Box>
  );
}
