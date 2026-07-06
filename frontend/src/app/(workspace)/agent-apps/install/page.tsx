"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import { useRouter } from "next/navigation";
import AgentAppInstallWizard from "@/components/agent-apps/AgentAppInstallWizard";
import PageHeader from "@/components/ui/PageHeader";
import { getCEUser } from "@/lib/ce-api";

export default function AgentAppInstallPage() {
  const router = useRouter();
  const user = getCEUser();
  const allowPathInstall =
    user?.role === "admin" ||
    process.env.NEXT_PUBLIC_KEPRIX_DEV_MODE === "true";

  return (
    <Box>
      <PageHeader
        title="Install agent app"
        description="Upload a deployment bundle (.zip), validate the manifest, and install in one flow."
        actions={
          <Button variant="outlined" onClick={() => router.push("/agent-apps")}>
            Back to hub
          </Button>
        }
      />
      <AgentAppInstallWizard allowPathInstall={allowPathInstall} />
    </Box>
  );
}
