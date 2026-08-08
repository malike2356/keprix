"use client";

import CrmWorkflowCanvas from "@/components/crm/visual/CrmWorkflowCanvas";
import { useParams } from "next/navigation";

export default function CrmWorkflowDetailPage() {
  const params = useParams();
  const id = String(params?.id || "");
  if (!id) return null;
  return <CrmWorkflowCanvas workflowId={id} />;
}
