"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { Automation } from "@/lib/control-center-api";

type AutomationRulesProps = {
  automations: Automation[];
  onTrigger: (automationId: string) => void;
};

export default function AutomationRules({ automations, onTrigger }: AutomationRulesProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Scheduled automations
        </Typography>
        {automations.length === 0 ? (
          <Typography variant="body2">No automations configured.</Typography>
        ) : (
          automations.map((automation) => (
            <Box
              key={automation.id}
              sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}
            >
              <Box>
                <Typography variant="body2">{automation.name}</Typography>
                <Box sx={{ display: "flex", gap: 0.5, mt: 0.5 }}>
                  <Chip size="small" label={automation.trigger_type} />
                  {automation.playbook_id ? <Chip size="small" variant="outlined" label={automation.playbook_id} /> : null}
                </Box>
              </Box>
              <Button size="small" variant="outlined" onClick={() => onTrigger(automation.id)}>
                Run
              </Button>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
}
