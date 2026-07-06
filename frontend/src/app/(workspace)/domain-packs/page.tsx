"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import {
  createDomainPack,
  fetchDomainPacks,
  publishDomainPack,
  requestDomainPackReview,
  validateDomainPack,
  type DomainPack,
} from "@/lib/domain-packs-api";

export default function DomainPacksPage() {
  const { data, mutate } = useSWR("domain-packs", fetchDomainPacks);
  const [open, setOpen] = React.useState(false);
  const [domainName, setDomainName] = React.useState("");
  const [jurisdictions, setJurisdictions] = React.useState("GH");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const packs = data?.packs ?? [];

  const handleCreate = async () => {
    setError(null);
    try {
      await createDomainPack(
        domainName,
        jurisdictions.split(",").map((value) => value.trim()).filter(Boolean),
      );
      setOpen(false);
      setDomainName("");
      await mutate();
      setMessage(`Created domain pack ${domainName}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  };

  const handleValidate = async (pack: DomainPack) => {
    setError(null);
    try {
      const result = await validateDomainPack(pack.id, true);
      setMessage(result.ok ? `Pack ${pack.domain_name} is valid` : result.errors.join("; "));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
    }
  };

  const handleReview = async (pack: DomainPack) => {
    setError(null);
    try {
      await requestDomainPackReview(pack.id, `Review ${pack.domain_name} before publication`);
      await mutate();
      setMessage(`Review requested for ${pack.domain_name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review request failed");
    }
  };

  const handlePublish = async (pack: DomainPack) => {
    setError(null);
    try {
      const result = await publishDomainPack(pack.id, pack.review_status === "approved");
      setMessage(`Publish status: ${String(result.status)}`);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Domain Knowledge Packs"
        description="Create, validate, localize, and publish versioned domain packs with review gates for high-stakes sectors."
      />
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Button variant="contained" sx={{ mb: 2 }} onClick={() => setOpen(true)}>
        New domain pack
      </Button>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" } }}>
        {packs.map((pack) => (
          <Card key={pack.id} variant="outlined">
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1, mb: 1 }}>
                <Typography variant="h6">{pack.domain_name}</Typography>
                <Chip size="small" label={`v${pack.version}`} />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Jurisdictions: {(pack.jurisdictions || []).join(", ") || "none"}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
                <Chip size="small" label={pack.review_status} />
                {pack.review_required ? <Chip size="small" color="warning" label="review required" /> : null}
                {pack.hub_published ? <Chip size="small" color="success" label="published" /> : null}
              </Box>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Button size="small" variant="outlined" onClick={() => void handleValidate(pack)}>
                  Validate
                </Button>
                <Button size="small" variant="outlined" onClick={() => void handleReview(pack)}>
                  Request review
                </Button>
                <Button size="small" variant="contained" onClick={() => void handlePublish(pack)}>
                  Publish
                </Button>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New domain pack</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField label="Domain name" value={domainName} onChange={(e) => setDomainName(e.target.value)} />
          <TextField
            label="Jurisdictions (comma separated)"
            value={jurisdictions}
            onChange={(e) => setJurisdictions(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={!domainName.trim()} onClick={() => void handleCreate()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
