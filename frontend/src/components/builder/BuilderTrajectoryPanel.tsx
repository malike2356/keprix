"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Step from "@mui/material/Step";
import StepContent from "@mui/material/StepContent";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import Typography from "@mui/material/Typography";
import * as React from "react";
import DiffViewer from "@/components/mutation/DiffViewer";
import type { BuilderPatchStep } from "@/lib/builder-api";

type BuilderTrajectoryPanelProps = {
  steps: BuilderPatchStep[];
  needsTier3Approval?: boolean;
  approvalReason?: string;
  mutationId?: string;
};

export default function BuilderTrajectoryPanel({
  steps,
  needsTier3Approval,
  approvalReason,
  mutationId,
}: BuilderTrajectoryPanelProps) {
  const [activeStep, setActiveStep] = React.useState(0);

  React.useEffect(() => {
    if (steps.length > 0) {
      setActiveStep(steps.length - 1);
    }
  }, [steps.length]);

  if (!steps.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No trajectory steps recorded yet.
      </Typography>
    );
  }

  const approvalHref = mutationId
    ? `/dashboard/mutation/${mutationId}`
    : "/dashboard/mutation?status=staged";

  return (
    <Box>
      {needsTier3Approval ? (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            <Button component="a" href={approvalHref} size="small" color="inherit">
              Review mutation
            </Button>
          }
        >
          {approvalReason || "This patch is out of scope or needs Tier 3 approval before merge."}
        </Alert>
      ) : null}

      <Stepper activeStep={activeStep} orientation="vertical" nonLinear>
        {steps.map((step, index) => (
          <Step key={step.id} expanded>
            <StepLabel
              optional={
                step.timestamp ? (
                  <Typography variant="caption">{new Date(step.timestamp).toLocaleString()}</Typography>
                ) : undefined
              }
              onClick={() => setActiveStep(index)}
              sx={{ cursor: "pointer" }}
            >
              <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                {step.label}
                {step.needs_approval ? <Chip size="small" color="warning" label="approval" /> : null}
              </Box>
            </StepLabel>
            <StepContent>
              {step.summary ? (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {step.summary}
                </Typography>
              ) : null}
              {step.diff ? <DiffViewer diff={step.diff} defaultExpanded={index === activeStep} /> : null}
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}
