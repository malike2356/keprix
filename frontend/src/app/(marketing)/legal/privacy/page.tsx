import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
export const metadata = {
  title: "Privacy Policy",
};

export default function PrivacyPolicyPage() {
  return (
    <Box sx={{ py: { xs: 10, md: 14 }, bgcolor: "background.default", minHeight: "100%" }}>
      <Container maxWidth="md">
        <Typography variant="h3" sx={{ fontWeight: 800, mb: 3, color: "text.primary" }}>
          Privacy Policy
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8, mb: 2 }}>
          Keprix is self-hosted software. Your instance runs on infrastructure you control.
          Conversation data, memory documents, and configuration are stored on your server unless
          you explicitly connect external LLM or channel providers.
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8, mb: 2 }}>
          When you use cloud LLM APIs, prompts and responses are transmitted to those providers
          under their respective terms. Review each provider&apos;s data policy before enabling it.
        </Typography>
        <Typography sx={{ color: "text.secondary", lineHeight: 1.8 }}>
          For GDPR tooling (consent, DSAR, erasure), use the in-app Privacy centre after sign-in
          at <code>/privacy</code> on your workspace instance.
        </Typography>
      </Container>
    </Box>
  );
}
