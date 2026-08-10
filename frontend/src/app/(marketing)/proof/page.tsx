"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";

type ProofRow = {
  id: string;
  text: string;
  author: string;
  authorTitle?: string | null;
  platform: string;
  url: string;
  date: string;
  tags?: string[];
  product: string;
  status: string;
};

export default function ProofPage() {
  const [rows, setRows] = React.useState<ProofRow[]>([]);
  const [product, setProduct] = React.useState("all");
  const [tag, setTag] = React.useState("all");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetch("/api/social-proof/public")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load proof");
        return res.json();
      })
      .then((data) => setRows(Array.isArray(data.testimonials) ? data.testimonials : []))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const products = React.useMemo(
    () => Array.from(new Set(rows.map((r) => r.product))).sort(),
    [rows],
  );
  const tags = React.useMemo(
    () => Array.from(new Set(rows.flatMap((r) => r.tags || []))).sort(),
    [rows],
  );
  const filtered = rows.filter((r) => {
    if (product !== "all" && r.product !== product) return false;
    if (tag !== "all" && !(r.tags || []).includes(tag)) return false;
    return true;
  });

  React.useEffect(() => {
    const payload = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": filtered.map((t) => ({
        "@type": "Review",
        reviewBody: t.text,
        datePublished: t.date,
        url: t.url,
        author: { "@type": "Person", name: t.author, jobTitle: t.authorTitle || undefined },
      })),
    });
    let el = document.getElementById("keprix-proof-jsonld");
    if (!el) {
      el = document.createElement("script");
      el.id = "keprix-proof-jsonld";
      (el as HTMLScriptElement).type = "application/ld+json";
      document.head.appendChild(el);
    }
    el.textContent = payload;
  }, [filtered]);

  return (
    <Box>
      <Navbar />
      <Container maxWidth="md" sx={{ pt: 12, pb: 8 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Keprix proof
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3, maxWidth: 640 }}>
          Verifiable testimonials with source links. Human-approved only. No carousels and no paraphrased quotes.
        </Typography>

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
          <Select size="small" value={product} onChange={(e) => setProduct(String(e.target.value))}>
            <MenuItem value="all">All products</MenuItem>
            {products.map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </Select>
          <Select size="small" value={tag} onChange={(e) => setTag(String(e.target.value))}>
            <MenuItem value="all">All tags</MenuItem>
            {tags.map((t) => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </Select>
        </Box>

        {error ? <Typography color="error">{error}</Typography> : null}

        {filtered.map((row) => (
          <Box
            key={row.id}
            component="article"
            sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: 2, mb: 2 }}
          >
            <Typography component="blockquote" sx={{ m: 0, mb: 1.5 }}>
              {row.text}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
              <strong>{row.author}</strong>
              {row.authorTitle ? <span>{row.authorTitle}</span> : null}
              <a href={row.url} target="_blank" rel="noopener noreferrer">
                {row.platform} source
              </a>
              <time dateTime={row.date}>{row.date}</time>
            </Typography>
          </Box>
        ))}

        {!error && filtered.length === 0 ? (
          <Typography color="text.secondary">
            Approved testimonials will appear here after curation. Collected items stay private until a human approves them.
          </Typography>
        ) : null}
      </Container>
      <Footer />
    </Box>
  );
}
