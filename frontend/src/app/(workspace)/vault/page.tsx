"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import LockIcon from "@mui/icons-material/Lock";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import {
  createVaultItem,
  deleteVaultItem,
  getVaultItem,
  listVaultItems,
  lockVault,
  unlockVault,
  updateVaultItem,
  type VaultItemMeta,
} from "@/lib/vault-api";

const CATEGORIES = ["password", "api_key", "token", "note", "other"];

type ItemForm = {
  label: string;
  category: string;
  username: string;
  value: string;
  url: string;
};

const emptyForm = (): ItemForm => ({
  label: "",
  category: "password",
  username: "",
  value: "",
  url: "",
});

export default function VaultPage() {
  const [unlocked, setUnlocked] = React.useState(false);
  const [items, setItems] = React.useState<VaultItemMeta[]>([]);
  const [category, setCategory] = React.useState<string>("all");
  const [search, setSearch] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [unlockOpen, setUnlockOpen] = React.useState(false);
  const [masterPassword, setMasterPassword] = React.useState("");
  const [itemDialogOpen, setItemDialogOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<ItemForm>(emptyForm());

  const loadItems = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listVaultItems());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load vault");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (unlocked) {
      loadItems();
    }
  }, [unlocked, loadItems]);

  const filtered = items.filter((item) => {
    if (category !== "all" && item.category !== category) {
      return false;
    }
    if (!search.trim()) {
      return true;
    }
    const q = search.toLowerCase();
    return (
      item.label.toLowerCase().includes(q) ||
      (item.username || "").toLowerCase().includes(q) ||
      item.tags.some((tag) => tag.toLowerCase().includes(q))
    );
  });

  const handleUnlock = async () => {
    setError(null);
    try {
      await unlockVault(masterPassword);
      setUnlocked(true);
      setUnlockOpen(false);
      setMasterPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unlock failed");
    }
  };

  const handleLock = async () => {
    await lockVault();
    setUnlocked(false);
    setItems([]);
  };

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setItemDialogOpen(true);
  };

  const openEdit = async (itemId: string) => {
    setError(null);
    try {
      const item = await getVaultItem(itemId);
      setEditingId(itemId);
      setForm({
        label: item.label,
        category: item.category,
        username: item.username || "",
        value: item.value || "",
        url: item.url || "",
      });
      setItemDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open item");
    }
  };

  const handleSave = async () => {
    if (!form.label.trim() || !form.value.trim()) {
      return;
    }
    setError(null);
    try {
      if (editingId) {
        await updateVaultItem(editingId, form);
      } else {
        await createVaultItem(form);
      }
      setItemDialogOpen(false);
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const handleDelete = async (itemId: string) => {
    setError(null);
    try {
      await deleteVaultItem(itemId);
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (!unlocked) {
    return (
      <Box>
        <PageHeader
          title="Credentials Vault"
          description="Manage encrypted credentials by category."
          breadcrumbs={[
            { label: "Security", href: "/vault" },
            { label: "Vault" },
          ]}
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <EmptyState
          title="Vault locked"
          description="Unlock with your master password to view and manage stored credentials."
          icon={<LockIcon sx={{ fontSize: 48 }} />}
          actionLabel="Unlock vault"
          onAction={() => setUnlockOpen(true)}
        />
        <Dialog open={unlockOpen} onClose={() => setUnlockOpen(false)} fullWidth maxWidth="xs">
          <DialogTitle>Unlock vault</DialogTitle>
          <DialogContent>
            <TextField
              label="Master password"
              type="password"
              fullWidth
              autoFocus
              value={masterPassword}
              onChange={(e) => setMasterPassword(e.target.value)}
              sx={{ mt: 1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setUnlockOpen(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleUnlock}>
              Unlock
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Credentials Vault"
        description="Manage encrypted credentials by category."
        breadcrumbs={[
          { label: "Security", href: "/vault" },
          { label: "Vault" },
        ]}
        actions={
          <>
            <Button startIcon={<LockOpenIcon />} onClick={handleLock}>
              Lock
            </Button>
            <Button variant="contained" onClick={openCreate}>
              Add item
            </Button>
          </>
        }
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mb: 2 }}>
        <TextField
          label="Search"
          size="small"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 200, flex: 1 }}
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="vault-category-label">Category</InputLabel>
          <Select
            labelId="vault-category-label"
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            {CATEGORIES.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <SkeletonTable rows={6} columns={4} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No vault items"
          description="Add credentials, API keys, or notes to your encrypted vault."
          icon={<LockOpenIcon sx={{ fontSize: 48 }} />}
          actionLabel="Add item"
          onAction={openCreate}
        />
      ) : (
        <List sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
          {filtered.map((item) => (
            <ListItem
              key={item.id}
              secondaryAction={
                <Box>
                  <IconButton edge="end" onClick={() => openEdit(item.id)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton edge="end" onClick={() => handleDelete(item.id)}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
              }
            >
              <ListItemText
                primary={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                    <Typography fontWeight={600}>{item.label}</Typography>
                    <Chip size="small" label={item.category} />
                  </Box>
                }
                secondary={item.username || item.url || undefined}
              />
            </ListItem>
          ))}
        </List>
      )}

      <Dialog open={itemDialogOpen} onClose={() => setItemDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editingId ? "Edit item" : "Add item"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField label="Label" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
          <FormControl fullWidth>
            <InputLabel id="item-category-label">Category</InputLabel>
            <Select
              labelId="item-category-label"
              label="Category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {CATEGORIES.map((cat) => (
                <MenuItem key={cat} value={cat}>
                  {cat}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
          <TextField label="URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <TextField
            label="Secret value"
            type="password"
            value={form.value}
            onChange={(e) => setForm({ ...form, value: e.target.value })}
            multiline
            minRows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setItemDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
