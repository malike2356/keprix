"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Link from "next/link";

export default function BlogPage() {
  return (
    <Container maxWidth="md" sx={{ py: { xs: 8, md: 12 } }}>
      <Typography variant="h3" sx={{ fontWeight: 800, mb: 2 }}>
        Blog
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 4, lineHeight: 1.75 }}>
        Product updates and engineering notes are published on GitHub Discussions and the changelog
        until the dedicated blog launches.
      </Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        <Button component={Link} href="/changelog" variant="contained">
          Read the changelog
        </Button>
        <Button
          component="a"
          href="https://github.com/malike2356/keprix/discussions"
          target="_blank"
          rel="noopener noreferrer"
          variant="outlined"
        >
          GitHub Discussions
        </Button>
      </Box>
    </Container>
  );
}
