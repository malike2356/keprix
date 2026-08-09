"use client";

import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";
import useSWR from "swr";
import CrmDetailEditor from "@/components/crm/CrmDetailEditor";
import { CRM_WORKSPACE, type CrmRecord } from "@/components/crm/types";
import { fetchCrmRecord } from "@/lib/crm-api";

export default function CrmDealDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detail = useSWR(id ? ["crm-deal", CRM_WORKSPACE, id] : null, () =>
    fetchCrmRecord("deals", id, CRM_WORKSPACE),
  );

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading deal...</Typography>;
  }

  const record = detail.data?.record as CrmRecord | undefined;
  if (!record) {
    return (
      <Typography color="text.secondary">
        Deal not found.{" "}
        <Typography component="a" href="/crm/deals" color="primary" sx={{ textDecoration: "underline" }}>
          Back to deals
        </Typography>
      </Typography>
    );
  }

  return (
    <CrmDetailEditor
      kind="deals"
      record={record}
      backHref="/crm/deals"
      backLabel="All deals"
      onSaved={() => void detail.mutate()}
      fields={[
        { key: "name", label: "Name" },
        { key: "account_id", label: "Account id" },
        { key: "source", label: "Source" },
        { key: "assigned_agent", label: "Assigned agent" },
        { key: "tags", label: "Tags (comma separated)" },
      ]}
    />
  );
}
