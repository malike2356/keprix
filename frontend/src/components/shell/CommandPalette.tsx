"use client";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconSearch } from "@tabler/icons-react";
import Fuse from "fuse.js";
import { useRouter } from "next/navigation";
import * as React from "react";
import NavIcon from "@/components/ui/NavIcon";
import { launcherCards, navigationFromContract } from "@/lib/navigation";
import type { UiContract } from "@/lib/ui-contract";

type CommandPaletteProps = {
  open: boolean;
  onClose: () => void;
  contract?: UiContract | null;
};

type CommandItem = {
  id: string;
  label: string;
  href: string;
  description?: string;
  icon: string;
};

export default function CommandPalette({ open, onClose, contract }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  const allItems = React.useMemo(() => {
    const { items } = navigationFromContract(contract ?? null);
    const commands: CommandItem[] = items.map((item) => ({
      id: item.id,
      label: item.label,
      href: item.href,
      description: item.description,
      icon: item.icon,
    }));

    for (const card of launcherCards) {
      if (!commands.some((item) => item.id === card.id)) {
        commands.push({
          id: card.id,
          label: card.title,
          href: card.href,
          description: card.description,
          icon: card.icon,
        });
      }
    }

    for (const action of contract?.actions || []) {
      if (!action.href || commands.some((item) => item.id === action.id)) {
        continue;
      }
      commands.push({
        id: action.id,
        label: action.label,
        href: action.href,
        description: action.surface.join(", "),
        icon: "hub",
      });
    }

    return commands;
  }, [contract]);

  const fuse = React.useMemo(
    () =>
      new Fuse(allItems, {
        keys: ["label", "description"],
        threshold: 0.35,
      }),
    [allItems],
  );

  const results = query.trim() ? fuse.search(query).map((r) => r.item) : allItems.slice(0, 12);

  React.useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const navigate = (href: string) => {
    onClose();
    router.push(href);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: { mt: -8 } }}>
      <Box sx={{ p: 2 }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder="Search pages and actions..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <IconSearch size={18} stroke={1.75} />
              </InputAdornment>
            ),
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && results[0]) {
              navigate(results[0].href);
            }
          }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Press Enter to open the first result. Esc to close.
        </Typography>
      </Box>
      <List dense sx={{ maxHeight: 360, overflowY: "auto", pb: 1 }}>
        {results.map((item) => (
          <ListItemButton key={item.id} onClick={() => navigate(item.href)}>
            <ListItemIcon sx={{ minWidth: 36 }}>
              <NavIcon name={item.icon} size={18} />
            </ListItemIcon>
            <ListItemText primary={item.label} secondary={item.description} />
          </ListItemButton>
        ))}
        {results.length === 0 && (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No matching pages.
            </Typography>
          </Box>
        )}
      </List>
    </Dialog>
  );
}
