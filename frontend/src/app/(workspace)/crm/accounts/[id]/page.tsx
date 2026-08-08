"use client";

import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import CrmDetailEditor from "@/components/crm/CrmDetailEditor";
import { CRM_WORKSPACE, type CrmRecord } from "@/components/crm/types";
import { fetchCrmRecord } from "@/lib/crm-api";

export default function CrmAccountDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detail = useSWR(id ? ["crm-account", CRM_WORKSPACE, id] : null, () =>
    fetchCrmRecord("accounts", id, CRM_WORKSPACE),
  );

  if (detail.isLoading && !detail.data) {
    return <Typography color="text.secondary">Loading account...</Typography>;
  }

  const record = detail.data?.record as CrmRecord | undefined;
  if (!record) {
    return (
      <Typography color="text.secondary">
        Account not found.{" "}
        <Typography component={Link} href="/crm/accounts" color="primary" sx={{ textDecoration: "underline" }}>
          Back to accounts
        </Typography>
      </Typography>
    );
  }

  return (
    <CrmDetailEditor
      kind="accounts"
      record={record}
      backHref="/crm/accounts"
      backLabel="All accounts"
      onSaved={() => void detail.mutate()}
      fields={[
        { key: "name", label: "Name" },
        { key: "domain", label: "Domain" },
        { key: "company_number", label: "Company number" },
        { key: "email", label: "Email" },
        { key: "source", label: "Source" },
        { key: "assigned_agent", label: "Assigned agent" },
        { key: "tags", label: "Tags (comma separated)" },
      ]}
    />
  );
}
