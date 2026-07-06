"use client";

import Box from "@mui/material/Box";
import DocumentAgentPanel from "@/components/documents/DocumentAgentPanel";
import IndexManagerPanel from "@/components/documents/IndexManagerPanel";
import PageHeader from "@/components/ui/PageHeader";

export default function DocumentAgentsPage() {
  return (
    <Box>
      <PageHeader
        title="Document agents"
        description="Upload documents, manage indexes, and ask cited questions across your corpus."
      />
      <Box sx={{ display: "grid", gap: 2 }}>
        <IndexManagerPanel />
        <DocumentAgentPanel />
      </Box>
    </Box>
  );
}
