"use client";

import { Suspense } from "react";
import Typography from "@mui/material/Typography";
import CrmPipelineBoard from "@/components/crm/visual/CrmPipelineBoard";

export default function CrmPipelinePage() {
  return (
    <Suspense fallback={<Typography color="text.secondary">Loading pipeline...</Typography>}>
      <CrmPipelineBoard />
    </Suspense>
  );
}
