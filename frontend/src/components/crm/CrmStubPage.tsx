"use client";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type CrmStubPageProps = {
  title: string;
  summary: string;
  ownerPrompt: string;
};

export function CrmStubPage({ title, summary, ownerPrompt }: CrmStubPageProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {summary}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Coming in later prompts ({ownerPrompt}). This route is reserved so the CRM IA stays stable.
          </Typography>
          <Typography variant="body2">
            Meanwhile use{" "}
            <Typography component="a" href="/crm" color="primary" sx={{ textDecoration: "underline" }}>
              CRM overview
            </Typography>
            , Soft Wall{" "}
            <Typography component="a" href="/outreach" color="primary" sx={{ textDecoration: "underline" }}>
              outreach
            </Typography>
            , or create records under leads, contacts, accounts, deals, and lists.
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default CrmStubPage;
