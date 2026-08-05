import Box from "@mui/material/Box";

export default function EmbedBookLayout({ children }: { children: React.ReactNode }) {
  return <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>{children}</Box>;
}
