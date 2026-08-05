import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
export const metadata = {
  title: "Terms of Use",
};

export default function TermsPage() {
  return (
    <Box sx={{ py: { xs: 10, md: 14 }, bgcolor: "background.default", minHeight: "100%" }}>
      <Container maxWidth="md">
        <Typography variant="h3" sx={{ fontWeight: 800, mb: 3, color: "text.primary" }}>
          Terms of Use
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8, mb: 2 }}>
          Keprix is distributed under the MIT License. You may use, copy, modify, merge, publish,
          distribute, sublicense, and sell copies of the software subject to the license conditions
          in the repository LICENSE file.
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8, mb: 2 }}>
          The software is provided &quot;as is&quot;, without warranty of any kind. You are responsible
          for securing your deployment, managing API keys, and ensuring compliance with laws that
          apply to your use case and jurisdiction.
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8 }}>
          Optional add-ons such as governance connectors are separate products with their
          own commercial terms from the provider.
        </Typography>
      </Container>
    </Box>
  );
}
