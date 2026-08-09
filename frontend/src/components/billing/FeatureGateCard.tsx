"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import LockIcon from "@mui/icons-material/Lock";

type Props = {
  title: string;
  description: string;
  requiredPlan?: string;
  upgradeHref?: string;
};

export default function FeatureGateCard({
  title,
  description,
  requiredPlan = "Pro",
  upgradeHref = "/pricing",
}: Props) {
  return (
    <Alert
      severity="info"
      icon={<LockIcon fontSize="small" />}
      sx={{ alignItems: "flex-start" }}
      action={
        <Button component="a" href={upgradeHref} size="small" color="inherit">
          View plans
        </Button>
      }
    >
      <Box>
        <Typography variant="subtitle2">{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {description} Available on {requiredPlan} and above.
        </Typography>
      </Box>
    </Alert>
  );
}
