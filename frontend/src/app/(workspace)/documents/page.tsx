"use client";

import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import * as React from "react";
import DocumentAgentPanel from "@/components/documents/DocumentAgentPanel";
import IndexManagerPanel from "@/components/documents/IndexManagerPanel";
import LegacyWorkspaceDocuments from "@/components/documents/LegacyWorkspaceDocuments";
import DocumentVaultExplorer from "@/components/document-vault/DocumentVaultExplorer";

export default function DocumentsPage() {
  const [tab, setTab] = React.useState(0);

  return (
    <Box>
      <Tabs
        value={tab}
        onChange={(_, next) => setTab(next)}
        sx={{ mb: 2 }}
        aria-label="Document surfaces"
      >
        <Tab label="Document Vault" />
        <Tab label="Legacy docs" />
        <Tab label="Agents" />
        <Tab label="Indexes" />
      </Tabs>
      {tab === 0 ? <DocumentVaultExplorer showHostFsLink /> : null}
      {tab === 1 ? <LegacyWorkspaceDocuments /> : null}
      {tab === 2 ? <DocumentAgentPanel /> : null}
      {tab === 3 ? <IndexManagerPanel /> : null}
    </Box>
  );
}
