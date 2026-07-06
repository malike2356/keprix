"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import PageContainer from "@/components/shared/PageContainer";

export default function AdminSectionPage({ title, description }: { title: string; description: string }) {
  return (
    <PageContainer title={title} description={description} padded={false}>
      <Box sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary">
          This admin section is scaffolded. Connect operational views in Prompt 137.
        </Typography>
      </Box>
    </PageContainer>
  );
}
