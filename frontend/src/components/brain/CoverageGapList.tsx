"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Link from "next/link";

type Props = {
  gaps: string[];
  counts?: Record<string, number>;
};

export default function CoverageGapList({ gaps, counts = {} }: Props) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Coverage gaps (thin topic areas)</Typography>
      {gaps.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No thin topic areas detected.</Typography>
      ) : (
        <List dense>
          {gaps.map((gap) => (
            <ListItem
              key={gap}
              disableGutters
              secondaryAction={
                <Button size="small" component={Link} href="/memory">
                  Add memory
                </Button>
              }
            >
              <ListItemText
                primary={`"${gap}"`}
                secondary={`${counts[gap] ?? 0} memor${(counts[gap] ?? 0) === 1 ? "y" : "ies"}`}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
}
