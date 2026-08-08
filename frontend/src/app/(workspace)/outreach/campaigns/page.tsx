"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import type { OutreachCampaign } from "@/components/outreach/types";
import {
  createOutreachCampaign,
  fetchOutreachCampaigns,
  patchOutreachCampaign,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

type Draft = {
  name: string;
  objective: string;
  active: boolean;
  daily_cap: string;
  timezone: string;
  require_approval: boolean;
  default_sequence_id: string;
  default_booking_link: string;
};

function toDraft(campaign: OutreachCampaign): Draft {
  return {
    name: campaign.name,
    objective: campaign.objective ?? "",
    active: campaign.active ?? campaign.status !== "paused",
    daily_cap: String(campaign.daily_cap ?? 10),
    timezone: campaign.timezone ?? "Europe/London",
    require_approval: campaign.require_approval ?? true,
    default_sequence_id: campaign.default_sequence_id ?? "",
    default_booking_link: campaign.default_booking_link ?? "",
  };
}

export default function OutreachCampaignsPage() {
  const [name, setName] = React.useState("");
  const [objective, setObjective] = React.useState("");
  const [drafts, setDrafts] = React.useState<Record<string, Draft>>({});
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const campaigns = useSWR(["outreach-campaigns", WORKSPACE], () => fetchOutreachCampaigns(WORKSPACE));

  React.useEffect(() => {
    const next: Record<string, Draft> = {};
    for (const campaign of campaigns.data?.campaigns ?? []) {
      next[campaign.id] = drafts[campaign.id] ?? toDraft(campaign);
    }
    setDrafts(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaigns.data]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!name.trim()) throw new Error("Campaign name is required");
      await createOutreachCampaign({ name: name.trim(), objective: objective.trim() || undefined }, WORKSPACE);
      setName("");
      setObjective("");
      setMessage("Campaign created");
      await campaigns.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create campaign");
    } finally {
      setBusy(false);
    }
  };

  const onSave = async (campaignId: string) => {
    const draft = drafts[campaignId];
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      await patchOutreachCampaign(
        campaignId,
        {
          name: draft.name,
          objective: draft.objective,
          active: draft.active,
          status: draft.active ? "active" : "paused",
          daily_cap: Number(draft.daily_cap) || 1,
          timezone: draft.timezone,
          require_approval: draft.require_approval,
          default_sequence_id: draft.default_sequence_id.trim() || null,
          default_booking_link: draft.default_booking_link.trim() || null,
        },
        WORKSPACE,
      );
      setMessage("Campaign saved");
      await campaigns.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save campaign");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            New campaign
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <TextField size="small" fullWidth label="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <TextField
              size="small"
              fullWidth
              label="Objective"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
            />
            <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()}>
              Create
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {campaigns.isLoading && !campaigns.data ? (
        <Typography color="text.secondary">Loading campaigns...</Typography>
      ) : (campaigns.data?.campaigns ?? []).length === 0 ? (
        <Typography color="text.secondary">No campaigns yet.</Typography>
      ) : (
        <Stack spacing={1.5}>
          {(campaigns.data?.campaigns ?? []).map((campaign) => {
            const draft = drafts[campaign.id] ?? toDraft(campaign);
            return (
              <Card key={campaign.id} variant="outlined">
                <CardContent>
                  <Stack spacing={1.5}>
                    <TextField
                      size="small"
                      label="Name"
                      value={draft.name}
                      onChange={(e) => setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, name: e.target.value } }))}
                    />
                    <TextField
                      size="small"
                      label="Objective"
                      value={draft.objective}
                      onChange={(e) =>
                        setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, objective: e.target.value } }))
                      }
                    />
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                      <TextField
                        size="small"
                        label="Daily cap"
                        value={draft.daily_cap}
                        onChange={(e) =>
                          setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, daily_cap: e.target.value } }))
                        }
                      />
                      <TextField
                        size="small"
                        fullWidth
                        label="Timezone"
                        value={draft.timezone}
                        onChange={(e) =>
                          setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, timezone: e.target.value } }))
                        }
                      />
                    </Stack>
                    <TextField
                      size="small"
                      label="Default sequence ID"
                      value={draft.default_sequence_id}
                      onChange={(e) =>
                        setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, default_sequence_id: e.target.value } }))
                      }
                    />
                    <TextField
                      size="small"
                      label="Default booking link"
                      value={draft.default_booking_link}
                      onChange={(e) =>
                        setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, default_booking_link: e.target.value } }))
                      }
                    />
                    <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={draft.active}
                            onChange={(e) =>
                              setDrafts((c) => ({ ...c, [campaign.id]: { ...draft, active: e.target.checked } }))
                            }
                          />
                        }
                        label="Active"
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={draft.require_approval}
                            onChange={(e) =>
                              setDrafts((c) => ({
                                ...c,
                                [campaign.id]: { ...draft, require_approval: e.target.checked },
                              }))
                            }
                          />
                        }
                        label="Require Soft Wall approval"
                      />
                      <Button size="small" variant="contained" disabled={busy} onClick={() => void onSave(campaign.id)}>
                        Save
                      </Button>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}
