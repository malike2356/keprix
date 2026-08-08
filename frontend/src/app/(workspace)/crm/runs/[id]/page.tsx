"use client";

import CrmRunReplay from "@/components/crm/visual/CrmRunReplay";
import { useParams } from "next/navigation";

export default function CrmRunPage() {
  const params = useParams();
  const id = String(params?.id || "");
  if (!id) return null;
  return <CrmRunReplay runId={id} />;
}
