"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import AgentAppAutomate from "@/components/agent-apps/AgentAppAutomate";
import AgentAppDetail from "@/components/agent-apps/AgentAppDetail";
import AgentAppManageActions from "@/components/agent-apps/AgentAppManageActions";
import PageHeader from "@/components/ui/PageHeader";
import { fetchAgentApp } from "@/lib/agent-apps-api";

export default function AgentAppDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params?.slug ?? "";
  const { data, error, isLoading } = useSWR(slug ? ["agent-app", slug] : null, () => fetchAgentApp(slug));

  return (
    <Box>
      <PageHeader
        title={data?.app.display_name || slug}
        description={data?.app.description || "Run and configure this agent app."}
        actions={
          <Button variant="outlined" onClick={() => router.push("/agent-apps")}>
            Back to hub
          </Button>
        }
      />
      {isLoading ? <Typography variant="body2">Loading...</Typography> : null}
      {error ? (
        <Typography color="error" variant="body2">
          {error instanceof Error ? error.message : "Failed to load app"}
        </Typography>
      ) : null}
      {data?.app ? (
        <>
          <AgentAppManageActions appName={slug} app={data.app} />
          <AgentAppAutomate appName={slug} app={data.app} />
          <AgentAppDetail appName={slug} app={data.app} />
        </>
      ) : null}
    </Box>
  );
}
