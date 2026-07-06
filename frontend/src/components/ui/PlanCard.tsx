"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { IconCheck } from "@tabler/icons-react";

export type PlanFeature = { label: string; included: boolean };

type PlanCardProps = {
  name: string;
  price: string;
  interval?: string;
  description?: string;
  features: PlanFeature[];
  highlighted?: boolean;
  loading?: boolean;
  onSelect?: () => void;
};

export default function PlanCard({
  name,
  price,
  interval = "month",
  description,
  features,
  highlighted = false,
  loading = false,
  onSelect,
}: PlanCardProps) {
  return (
    <Card variant={highlighted ? "elevation" : "outlined"} sx={{ height: "100%", borderColor: highlighted ? "primary.main" : undefined }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
          <Typography variant="h6">{name}</Typography>
          {highlighted ? <Chip size="small" color="primary" label="Recommended" /> : null}
        </Box>
        <Typography variant="h4" fontWeight={700}>{price}</Typography>
        <Typography variant="caption" color="text.secondary">per {interval}</Typography>
        {description ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{description}</Typography>
        ) : null}
        <List dense sx={{ mt: 1 }}>
          {features.map((feature) => (
            <ListItem key={feature.label} disableGutters>
              <ListItemIcon sx={{ minWidth: 28 }}>
                <IconCheck size={16} stroke={1.75} style={{ opacity: feature.included ? 1 : 0.35 }} />
              </ListItemIcon>
              <ListItemText primary={feature.label} />
            </ListItem>
          ))}
        </List>
      </CardContent>
      <CardActions>
        <Button fullWidth variant={highlighted ? "contained" : "outlined"} disabled={loading} onClick={onSelect}>
          Choose plan
        </Button>
      </CardActions>
    </Card>
  );
}
