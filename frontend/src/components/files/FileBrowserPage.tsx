"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CreateNewFolderOutlinedIcon from "@mui/icons-material/CreateNewFolderOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { useRequireAdmin } from "@/lib/ce-auth";
import {
  getFilesystemDefaultCwd,
  getFilesystemGitRoot,
  humanizeFsError,
  importFilesystemPathToDocuments,
  listFilesystemEntries,
  mkdirFilesystem,
  readFilesystemDataUrl,
  readFilesystemText,
  uploadFilesystemFile,
  type FsEntry,
} from "@/lib/filesystem-api";

type RootMode = "workspace" | "git" | "system";

type PreviewState =
  | null
  | {
      kind: "text";
      path: string;
      text: string;
      byteSize: number;
      mimeType: string;
      truncated: boolean;
    }
  | {
      kind: "image";
      path: string;
      dataUrl: string;
      byteSize: number;
      mimeType: string;
    }
  | {
      kind: "binary";
      path: string;
      byteSize: number;
      mimeType: string;
      note: string;
    };

const ROOT_MODE_KEY = "keprix-files-root-mode";
const SYSTEM_UNLOCK_KEY = "keprix-files-system-root-unlocked";

function cleanPath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || trimmed === "/") return "/";
  const prefixed = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return prefixed.replace(/\/+$/, "") || "/";
}

function parentPath(path: string): string {
  const current = cleanPath(path);
  if (current === "/") return "/";
  const parts = current.split("/").filter(Boolean);
  parts.pop();
  return parts.length > 0 ? `/${parts.join("/")}` : "/";
}

function pathName(path: string): string {
  const parts = cleanPath(path).split("/").filter(Boolean);
  return parts[parts.length - 1] || "/";
}

function joinPath(base: string, name: string): string {
  const root = cleanPath(base);
  const leaf = name.replace(/^\/+|\/+$/g, "").trim();
  if (!leaf) return root;
  return root === "/" ? `/${leaf}` : `${root}/${leaf}`;
}

function isUnderRoot(path: string, root: string): boolean {
  const current = cleanPath(path);
  const base = cleanPath(root);
  if (base === "/") return current.startsWith("/");
  return current === base || current.startsWith(`${base}/`);
}

function pathAncestors(path: string, root: string): string[] {
  const current = cleanPath(path);
  const base = cleanPath(root);
  if (!isUnderRoot(current, base)) {
    return [base];
  }
  if (base === "/") {
    const parts = current.split("/").filter(Boolean);
    const out = ["/"];
    let acc = "";
    for (const part of parts) {
      acc += `/${part}`;
      out.push(acc);
    }
    return out;
  }
  const baseParts = base.split("/").filter(Boolean);
  const currentParts = current.split("/").filter(Boolean);
  const out = [base];
  let acc = `/${baseParts.join("/")}`;
  for (let i = baseParts.length; i < currentParts.length; i += 1) {
    acc += `/${currentParts[i]}`;
    out.push(acc);
  }
  return out;
}

function sortEntries(entries: FsEntry[]): FsEntry[] {
  return [...entries].sort((left, right) => {
    if (left.isDirectory !== right.isDirectory) {
      return left.isDirectory ? -1 : 1;
    }
    return left.name.localeCompare(right.name);
  });
}

function humanSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatTime(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function rootLabel(mode: RootMode, workspaceRoot: string, gitRoot: string | null): string {
  if (mode === "workspace") return `Workspace root: ${workspaceRoot}`;
  if (mode === "git") return `Git root: ${gitRoot || workspaceRoot}`;
  return "System root: /";
}

function usePrevious<T>(value: T): T | undefined {
  const ref = React.useRef<T | undefined>(undefined);
  React.useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref.current;
}

export default function FileBrowserPage() {
  const { user, isLoading, isAdmin } = useRequireAdmin();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [workspaceRoot, setWorkspaceRoot] = React.useState("/");
  const [gitRoot, setGitRoot] = React.useState<string | null>(null);
  const [shortcuts, setShortcuts] = React.useState<{ data?: string; home?: string; docs?: string }>({});
  const [rootMode, setRootMode] = React.useState<RootMode>("workspace");
  const [systemUnlocked, setSystemUnlocked] = React.useState(false);
  const [unlockDialogOpen, setUnlockDialogOpen] = React.useState(false);
  const [currentPath, setCurrentPath] = React.useState("/");
  const [pathInput, setPathInput] = React.useState("/");
  const [expandedPaths, setExpandedPaths] = React.useState<string[]>(["/"]);
  const [entriesByPath, setEntriesByPath] = React.useState<Record<string, FsEntry[]>>({});
  const [loadingPaths, setLoadingPaths] = React.useState<Record<string, boolean>>({});
  const [folderErrors, setFolderErrors] = React.useState<Record<string, string>>({});
  const [preview, setPreview] = React.useState<PreviewState>(null);
  const [globalError, setGlobalError] = React.useState<string | null>(null);
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null);
  const [busyAction, setBusyAction] = React.useState(false);
  const [newFolderName, setNewFolderName] = React.useState("");
  const [booting, setBooting] = React.useState(true);
  const previousCurrentPath = usePrevious(currentPath);
  const uploadInputRef = React.useRef<HTMLInputElement | null>(null);

  const resolvedRoot = React.useMemo(() => {
    if (rootMode === "workspace") return cleanPath(workspaceRoot);
    if (rootMode === "git") return cleanPath(gitRoot || workspaceRoot);
    return systemUnlocked ? "/" : cleanPath(workspaceRoot);
  }, [gitRoot, rootMode, systemUnlocked, workspaceRoot]);

  const selectedRootLabel = rootLabel(rootMode, workspaceRoot, gitRoot);
  const currentEntries = entriesByPath[currentPath] || [];
  const selectedEntry = React.useMemo(
    () => currentEntries.find((entry) => entry.path === currentPath) || null,
    [currentEntries, currentPath],
  );

  React.useEffect(() => {
    const storedMode = window.localStorage.getItem(ROOT_MODE_KEY) as RootMode | null;
    const storedUnlocked = window.localStorage.getItem(SYSTEM_UNLOCK_KEY) === "true";
    if (storedMode === "workspace" || storedMode === "git" || storedMode === "system") {
      setRootMode(storedMode);
    }
    setSystemUnlocked(storedUnlocked);
  }, []);

  React.useEffect(() => {
    let active = true;
    const bootstrap = async () => {
      try {
        const defaultCwd = await getFilesystemDefaultCwd();
        if (!active) return;
        const nextWorkspace = cleanPath(defaultCwd?.cwd || "/data/keprix");
        setWorkspaceRoot(nextWorkspace);
        setShortcuts(defaultCwd?.shortcuts || {});
        const nextGitRoot = await getFilesystemGitRoot(nextWorkspace);
        if (!active) return;
        setGitRoot(nextGitRoot ? cleanPath(nextGitRoot) : null);
      } catch (error) {
        if (active) {
          setGlobalError(error instanceof Error ? error.message : "Failed to load filesystem roots");
        }
      } finally {
        if (active) {
          setBooting(false);
        }
      }
    };
    void bootstrap();
    return () => {
      active = false;
    };
  }, []);

  React.useEffect(() => {
    if (booting) return;
    const queryPath = cleanPath(searchParams.get("path") || resolvedRoot);
    const nextPath = isUnderRoot(queryPath, resolvedRoot) || rootMode === "system" ? queryPath : resolvedRoot;
    if (nextPath !== currentPath) {
      setCurrentPath(nextPath);
      setPathInput(nextPath);
      setPreview(null);
    }
  }, [booting, currentPath, resolvedRoot, rootMode, searchParams]);

  React.useEffect(() => {
    window.localStorage.setItem(ROOT_MODE_KEY, rootMode);
  }, [rootMode]);

  React.useEffect(() => {
    window.localStorage.setItem(SYSTEM_UNLOCK_KEY, String(systemUnlocked));
  }, [systemUnlocked]);

  React.useEffect(() => {
    if (booting) return;
    if (!isUnderRoot(currentPath, resolvedRoot) && rootMode !== "system") {
      setCurrentPath(resolvedRoot);
      setPathInput(resolvedRoot);
      router.replace(`${pathname}?path=${encodeURIComponent(resolvedRoot)}`);
      return;
    }
    const nextAncestors = pathAncestors(currentPath, resolvedRoot);
    setExpandedPaths((previous) => Array.from(new Set([...previous, ...nextAncestors])));
  }, [booting, currentPath, pathname, resolvedRoot, rootMode, pathInput, router]);

  React.useEffect(() => {
    if (previousCurrentPath !== currentPath) {
      setPathInput(currentPath);
    }
  }, [currentPath, previousCurrentPath]);

  React.useEffect(() => {
    const next = expandedPaths.filter((path) => path === resolvedRoot || isUnderRoot(path, resolvedRoot) || rootMode === "system");
    for (const path of next) {
      if (!entriesByPath[path] && !loadingPaths[path]) {
        void loadFolder(path);
      }
    }
  }, [expandedPaths, entriesByPath, loadingPaths, resolvedRoot, rootMode]);

  React.useEffect(() => {
    if (!entriesByPath[resolvedRoot] && !loadingPaths[resolvedRoot]) {
      void loadFolder(resolvedRoot);
    }
  }, [entriesByPath, loadingPaths, resolvedRoot]);

  const loadFolder = React.useCallback(async (path: string) => {
    const target = cleanPath(path);
    if (loadingPaths[target]) {
      return;
    }

    setLoadingPaths((previous) => ({ ...previous, [target]: true }));
    setFolderErrors((previous) => {
      const next = { ...previous };
      delete next[target];
      return next;
    });

    try {
      const result = await listFilesystemEntries(target);
      setEntriesByPath((previous) => ({ ...previous, [target]: sortEntries(result.entries) }));
      if (result.error) {
        setFolderErrors((previous) => ({
          ...previous,
          [target]: humanizeFsError(result.error, result.message),
        }));
      }
    } catch (error) {
      setFolderErrors((previous) => ({
        ...previous,
        [target]: error instanceof Error ? error.message : "Failed to load folder",
      }));
      setEntriesByPath((previous) => ({ ...previous, [target]: [] }));
    } finally {
      setLoadingPaths((previous) => {
        const next = { ...previous };
        delete next[target];
        return next;
      });
    }
  }, [loadingPaths]);

  const commitPath = React.useCallback(
    (nextPath: string) => {
      const target = cleanPath(nextPath);
      if (rootMode !== "system" && !isUnderRoot(target, resolvedRoot)) {
        setGlobalError(`Path must stay under ${resolvedRoot}`);
        return;
      }
      setGlobalError(null);
      router.replace(`${pathname}?path=${encodeURIComponent(target)}`);
    },
    [pathname, resolvedRoot, router, rootMode],
  );

  const handleSelectRoot = React.useCallback(
    (mode: RootMode) => {
      if (mode === "system" && !systemUnlocked) {
        setUnlockDialogOpen(true);
        return;
      }
      setRootMode(mode);
      const nextRoot = mode === "workspace" ? workspaceRoot : mode === "git" ? (gitRoot || workspaceRoot) : "/";
      router.replace(`${pathname}?path=${encodeURIComponent(cleanPath(nextRoot))}`);
      setCurrentPath(cleanPath(nextRoot));
      setPathInput(cleanPath(nextRoot));
      setPreview(null);
    },
    [gitRoot, pathname, router, systemUnlocked, workspaceRoot],
  );

  const openPath = React.useCallback(
    (nextPath: string) => {
      const target = cleanPath(nextPath);
      if (rootMode !== "system" && !isUnderRoot(target, resolvedRoot)) {
        setGlobalError(`Path must stay under ${resolvedRoot}`);
        return;
      }
      setCurrentPath(target);
      setPathInput(target);
      setPreview(null);
      router.replace(`${pathname}?path=${encodeURIComponent(target)}`);
    },
    [pathname, resolvedRoot, router, rootMode],
  );

  const toggleExpanded = React.useCallback((path: string) => {
    const target = cleanPath(path);
    setExpandedPaths((previous) =>
      previous.includes(target) ? previous.filter((item) => item !== target) : [...previous, target],
    );
  }, []);

  const previewFile = React.useCallback(async (path: string) => {
    const target = cleanPath(path);
    setGlobalError(null);
    try {
      const text = await readFilesystemText(target);
      if (!text.binary) {
        setPreview({
          kind: "text",
          path: target,
          text: text.text,
          byteSize: text.byteSize,
          mimeType: text.mimeType,
          truncated: text.truncated,
        });
        return;
      }
      if (text.mimeType.startsWith("image/") && text.byteSize <= 5 * 1024 * 1024) {
        const dataUrl = await readFilesystemDataUrl(target);
        setPreview({
          kind: "image",
          path: target,
          dataUrl,
          byteSize: text.byteSize,
          mimeType: text.mimeType,
        });
        return;
      }
      setPreview({
        kind: "binary",
        path: target,
        byteSize: text.byteSize,
        mimeType: text.mimeType,
        note: text.truncated ? "Text preview was truncated." : "Binary file preview is not available.",
      });
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : "Failed to load file preview");
    }
  }, []);

  const runAction = React.useCallback(async (label: string, action: () => Promise<void>) => {
    setBusyAction(true);
    setGlobalError(null);
    setStatusMessage(null);
    try {
      await action();
      setStatusMessage(label);
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : label);
    } finally {
      setBusyAction(false);
    }
  }, []);

  const handleCreateFolder = React.useCallback(() => {
    const name = newFolderName.trim();
    if (!name) {
      setGlobalError("Enter a folder name");
      return;
    }
    const target = joinPath(currentPath, name);
    void runAction(`Created ${target}`, async () => {
      await mkdirFilesystem(target);
      setNewFolderName("");
      await loadFolder(currentPath);
      setExpandedPaths((previous) => (previous.includes(currentPath) ? previous : [...previous, currentPath]));
    });
  }, [currentPath, loadFolder, newFolderName, runAction]);

  const handleUploadFiles = React.useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      void runAction(`Uploaded ${files.length} file${files.length === 1 ? "" : "s"}`, async () => {
        for (const file of Array.from(files)) {
          await uploadFilesystemFile(currentPath, file);
        }
        await loadFolder(currentPath);
        setExpandedPaths((previous) =>
          previous.includes(currentPath) ? previous : [...previous, currentPath],
        );
      });
    },
    [currentPath, loadFolder, runAction],
  );

  const handleCopyPath = React.useCallback(async (path: string) => {
    try {
      await navigator.clipboard.writeText(path);
      setStatusMessage(`Copied ${path}`);
    } catch {
      setGlobalError("Could not copy path");
    }
  }, []);

  const handleImportToDocuments = React.useCallback(
    (path: string) => {
      void runAction("Imported into Documents", async () => {
        const doc = await importFilesystemPathToDocuments(path);
        setStatusMessage(`Imported as "${doc.title}" (Documents / files)`);
      });
    },
    [runAction],
  );

  const renderFolder = React.useCallback(
    (path: string, depth: number): React.ReactNode => {
      const target = cleanPath(path);
      const entries = entriesByPath[target] || [];
      const isOpen = expandedPaths.includes(target);
      const isRoot = target === resolvedRoot;
      const isLoading = Boolean(loadingPaths[target]);
      const error = folderErrors[target];

      const folderTitle = isRoot ? selectedRootLabel : pathName(target);

      return (
        <Box key={target} sx={{ pl: depth > 0 ? 1.5 : 0 }}>
          <ListItemButton
            selected={currentPath === target}
            onClick={() => {
              setCurrentPath(target);
              setPathInput(target);
              setPreview(null);
              toggleExpanded(target);
              void loadFolder(target);
            }}
            sx={{
              borderRadius: 1,
              mb: 0.25,
              pl: 1,
              pr: 1,
              py: 0.5,
              bgcolor: currentPath === target ? "action.selected" : "transparent",
            }}
          >
            <ListItemIcon sx={{ minWidth: 32 }}>
              <Button
                size="small"
                variant="text"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  toggleExpanded(target);
                  void loadFolder(target);
                }}
                sx={{ minWidth: 0, p: 0.25, color: "text.secondary" }}
              >
                {isOpen ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
              </Button>
            </ListItemIcon>
            <ListItemText
              primary={folderTitle}
              secondary={error ? `Read issue: ${error}` : isLoading ? "Loading..." : target}
              primaryTypographyProps={{ noWrap: true, fontWeight: isRoot ? 700 : 500 }}
              secondaryTypographyProps={{ noWrap: true }}
            />
            <Chip size="small" label={isRoot ? "root" : "folder"} variant="outlined" />
          </ListItemButton>

          {isOpen && (
            <Box sx={{ pl: 1.5 }}>
              {entries.map((entry) =>
                entry.isDirectory ? (
                  renderFolder(entry.path, depth + 1)
                ) : (
                  <ListItemButton
                    key={entry.path}
                    selected={selectedEntry?.path === entry.path}
                    onClick={() => {
                      setCurrentPath(target);
                      setPathInput(target);
                      void previewFile(entry.path);
                    }}
                    sx={{
                      borderRadius: 1,
                      mb: 0.25,
                      pl: 1.5,
                      pr: 1,
                      py: 0.5,
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <InsertDriveFileOutlinedIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={entry.name}
                      secondary={
                        entry.size != null && !entry.isDirectory
                          ? `${humanSize(entry.size)} · ${entry.path}`
                          : entry.path
                      }
                      primaryTypographyProps={{ noWrap: true }}
                      secondaryTypographyProps={{ noWrap: true }}
                    />
                  </ListItemButton>
                ),
              )}
              {entries.length === 0 && !isLoading && !error ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 2, py: 1 }}>
                  Empty folder
                </Typography>
              ) : null}
            </Box>
          )}
        </Box>
      );
    },
    [
      currentPath,
      entriesByPath,
      expandedPaths,
      folderErrors,
      loadFolder,
      previewFile,
      resolvedRoot,
      selectedEntry?.path,
      selectedRootLabel,
      loadingPaths,
      toggleExpanded,
    ],
  );

  const pathCrumbs = cleanPath(currentPath).split("/").filter(Boolean);

  if (isLoading || booting) {
    return (
      <Box sx={{ width: "100%", py: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Loading files...
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: "100%",
        mx: { sm: -3 },
        mt: { sm: -3 },
        mb: { xs: 0, md: -3 },
        display: "flex",
        flexDirection: "column",
        height: { md: "calc(100vh - 112px)" },
        minHeight: { xs: "70vh", md: 0 },
        bgcolor: "background.default",
      }}
    >
      <Box
        sx={{
          px: { xs: 2, sm: 3 },
          pt: { xs: 2, sm: 2.5 },
          pb: 1.5,
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1.5,
            mb: 1.5,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h5" component="h1" fontWeight={700}>
              Files
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Browse, preview, upload, and open text into Documents.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              variant="outlined"
              onClick={() => {
                setPreview(null);
                setGlobalError(null);
                void loadFolder(currentPath);
              }}
            >
              Refresh
            </Button>
            <Button size="small" component="a" href="/documents" variant="text">
              Documents
            </Button>
            <Button size="small" component="a" href="/home" variant="text">
              Home
            </Button>
          </Stack>
        </Box>

        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "center" }}>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
            {(
              [
                { id: "workspace" as const, label: "Workspace", icon: <StorageOutlinedIcon fontSize="small" /> },
                { id: "git" as const, label: "Git", icon: <FolderOpenIcon fontSize="small" />, disabled: !gitRoot && !workspaceRoot },
                {
                  id: "system" as const,
                  label: "System",
                  icon: <ShieldOutlinedIcon fontSize="small" />,
                  disabled: !systemUnlocked,
                },
              ] as const
            ).map((root) => (
              <Button
                key={root.id}
                size="small"
                variant={rootMode === root.id ? "contained" : "outlined"}
                startIcon={root.icon}
                disabled={"disabled" in root ? Boolean(root.disabled) : false}
                onClick={() => handleSelectRoot(root.id)}
              >
                {root.label}
              </Button>
            ))}
            <Button size="small" variant="text" onClick={() => setUnlockDialogOpen(true)}>
              {systemUnlocked ? "System unlocked" : "Unlock system"}
            </Button>
          </Stack>

          <Box sx={{ flex: 1, minWidth: 220, display: "flex", gap: 1 }}>
            <TextField
              size="small"
              fullWidth
              label="Path"
              value={pathInput}
              onChange={(event) => setPathInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") commitPath(pathInput);
              }}
            />
            <Button variant="contained" onClick={() => commitPath(pathInput)}>
              Open
            </Button>
          </Box>
        </Stack>

        <Stack direction="row" spacing={0.75} sx={{ mt: 1.25 }} flexWrap="wrap" useFlexGap alignItems="center">
          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
            Jump:
          </Typography>
          {[
            { label: "Data", path: shortcuts.data || "/data/keprix" },
            { label: "Home", path: shortcuts.home || workspaceRoot },
            { label: "Docs", path: shortcuts.docs || `${shortcuts.data || "/data/keprix"}/docs` },
            { label: "Workspace root", path: workspaceRoot },
          ].map((item) => (
            <Chip
              key={item.label}
              size="small"
              label={item.label}
              variant="outlined"
              onClick={() => {
                setRootMode("workspace");
                openPath(item.path);
              }}
              sx={{ cursor: "pointer" }}
            />
          ))}
          <Chip size="small" color="default" label={selectedRootLabel} variant="outlined" />
        </Stack>
      </Box>

      {(globalError || statusMessage) && (
        <Box sx={{ px: { xs: 2, sm: 3 }, pt: 1.5 }}>
          {globalError ? (
            <Alert severity="error" onClose={() => setGlobalError(null)}>
              {globalError}
            </Alert>
          ) : null}
          {statusMessage ? (
            <Alert severity="success" sx={{ mt: globalError ? 1 : 0 }} onClose={() => setStatusMessage(null)}>
              {statusMessage}
            </Alert>
          ) : null}
        </Box>
      )}

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.15fr) minmax(320px, 0.85fr)" },
          borderTop: { xs: 1, lg: 0 },
          borderColor: "divider",
        }}
      >
        <Box
          sx={{
            minWidth: 0,
            minHeight: { xs: 420, lg: 0 },
            display: "flex",
            flexDirection: "column",
            borderRight: { lg: 1 },
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <Box
            sx={{
              px: 2,
              py: 1.25,
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: 1,
              borderColor: "divider",
            }}
          >
            <Breadcrumbs
              maxItems={5}
              itemsBeforeCollapse={1}
              itemsAfterCollapse={2}
              sx={{ minWidth: 0, "& .MuiBreadcrumbs-ol": { flexWrap: "nowrap" } }}
            >
              <Link
                component="button"
                type="button"
                underline="hover"
                color="inherit"
                onClick={() => commitPath(resolvedRoot)}
                sx={{ border: 0, background: "none", cursor: "pointer", p: 0, font: "inherit" }}
              >
                {rootMode === "system" ? "/" : pathName(resolvedRoot) || "root"}
              </Link>
              {pathCrumbs.map((segment, index) => {
                const crumbPath = `/${pathCrumbs.slice(0, index + 1).join("/")}`;
                const isLast = index === pathCrumbs.length - 1;
                if (isLast) {
                  return (
                    <Typography key={crumbPath} color="text.primary" variant="body2" fontWeight={600}>
                      {segment}
                    </Typography>
                  );
                }
                return (
                  <Link
                    key={crumbPath}
                    component="button"
                    type="button"
                    underline="hover"
                    color="inherit"
                    onClick={() => commitPath(crumbPath)}
                    sx={{ border: 0, background: "none", cursor: "pointer", p: 0, font: "inherit" }}
                  >
                    {segment}
                  </Link>
                );
              })}
            </Breadcrumbs>
            <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center", mr: 0.5 }}>
                {entriesByPath[currentPath] ? `${entriesByPath[currentPath].length} items` : ""}
              </Typography>
              <Button
                size="small"
                startIcon={<UploadFileOutlinedIcon />}
                disabled={busyAction}
                onClick={() => uploadInputRef.current?.click()}
              >
                Upload
              </Button>
              <Button size="small" startIcon={<ContentCopyIcon />} onClick={() => void handleCopyPath(currentPath)}>
                Copy path
              </Button>
              <Button
                size="small"
                startIcon={<FolderOpenIcon />}
                onClick={() => {
                  if (currentPath !== resolvedRoot || rootMode === "system") {
                    commitPath(parentPath(currentPath));
                  }
                }}
                disabled={currentPath === resolvedRoot && rootMode !== "system"}
              >
                Up
              </Button>
            </Stack>
          </Box>

          <input
            ref={uploadInputRef}
            type="file"
            multiple
            hidden
            onChange={(event) => {
              handleUploadFiles(event.target.files);
              event.target.value = "";
            }}
          />

          <Box sx={{ px: 2, py: 1, display: "flex", gap: 1, borderBottom: 1, borderColor: "divider" }}>
            <TextField
              size="small"
              fullWidth
              placeholder="New folder name"
              value={newFolderName}
              onChange={(event) => setNewFolderName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") handleCreateFolder();
              }}
            />
            <Button
              size="small"
              variant="outlined"
              startIcon={<CreateNewFolderOutlinedIcon />}
              disabled={busyAction}
              onClick={handleCreateFolder}
              sx={{ whiteSpace: "nowrap" }}
            >
              New folder
            </Button>
          </Box>

          <List dense disablePadding sx={{ flex: 1, overflow: "auto", minHeight: 0 }}>
            {folderErrors[resolvedRoot] && !(entriesByPath[resolvedRoot]?.length) ? (
              <Box sx={{ px: 2, py: 3 }}>
                <Alert severity="warning">{folderErrors[resolvedRoot]}</Alert>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                  Try Data, Docs, or Home above, or open a path under the workspace root.
                </Typography>
              </Box>
            ) : (
              renderFolder(resolvedRoot, 0)
            )}
          </List>
        </Box>

        <Box
          sx={{
            minWidth: 0,
            minHeight: { xs: 320, lg: 0 },
            display: "flex",
            flexDirection: "column",
            bgcolor: "background.default",
            p: 2,
          }}
        >
          <Typography variant="subtitle2" fontWeight={700} gutterBottom>
            Preview
          </Typography>
          {preview ? (
            <Stack spacing={1.5} sx={{ flex: 1, minHeight: 0 }}>
              <Box>
                <Typography variant="body2" fontWeight={600} noWrap title={preview.path}>
                  {pathName(preview.path)}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }} noWrap>
                  {preview.path}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {preview.mimeType} · {humanSize(preview.byteSize)}
                </Typography>
              </Box>

              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<ContentCopyIcon />}
                  onClick={() => void handleCopyPath(preview.path)}
                >
                  Copy path
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<DescriptionOutlinedIcon />}
                  disabled={busyAction || preview.kind === "binary"}
                  onClick={() => handleImportToDocuments(preview.path)}
                >
                  Open in Documents
                </Button>
              </Box>

              <Divider />

              {preview.kind === "text" ? (
                <>
                  {preview.truncated ? (
                    <Alert severity="info">Text preview truncated by the backend.</Alert>
                  ) : null}
                  <Box
                    component="pre"
                    sx={{
                      m: 0,
                      flex: 1,
                      overflow: "auto",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                      fontSize: "0.85rem",
                      lineHeight: 1.6,
                      bgcolor: "background.paper",
                      border: 1,
                      borderColor: "divider",
                      borderRadius: 1,
                      p: 1.5,
                    }}
                  >
                    {preview.text}
                  </Box>
                </>
              ) : preview.kind === "image" ? (
                <Box
                  component="img"
                  src={preview.dataUrl}
                  alt={preview.path}
                  sx={{ maxWidth: "100%", borderRadius: 1, border: 1, borderColor: "divider" }}
                />
              ) : (
                <Alert severity="info">{preview.note}</Alert>
              )}
            </Stack>
          ) : (
            <Box
              sx={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: 1,
                borderColor: "divider",
                borderStyle: "dashed",
                borderRadius: 1,
                px: 3,
                py: 4,
                textAlign: "center",
              }}
            >
              <Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Select a file to preview text or images.
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Upload into the current folder, then Open in Documents to bring text into the library.
                  Noise folders (node_modules, .git, venv) stay hidden.
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      </Box>

      <Dialog open={unlockDialogOpen} onClose={() => setUnlockDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Unlock system root browsing</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Enables browsing the full host filesystem from the web UI. Admin only; use when you need host-level inspection.
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={systemUnlocked}
                onChange={(_, checked) => {
                  setSystemUnlocked(checked);
                  if (checked) {
                    setRootMode("system");
                    setCurrentPath("/");
                    setPathInput("/");
                    router.replace(`${pathname}?path=%2F`);
                  } else {
                    setRootMode("workspace");
                    setCurrentPath(workspaceRoot);
                    setPathInput(workspaceRoot);
                    router.replace(`${pathname}?path=${encodeURIComponent(workspaceRoot)}`);
                  }
                }}
              />
            }
            label="I understand this exposes system paths"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnlockDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
