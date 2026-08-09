"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import {
  DataGrid,
  type GridColDef,
  type GridColumnVisibilityModel,
  type GridPaginationModel,
  type GridRowSelectionModel,
  type GridSortModel,
} from "@mui/x-data-grid";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import CrmLeadProvenanceDrawer from "@/components/crm/CrmLeadProvenanceDrawer";
import CrmLeadsBulkBar from "@/components/crm/CrmLeadsBulkBar";
import CrmLeadsImportExportToolbar from "@/components/crm/CrmLeadsImportExportToolbar";
import CrmSavedViewsBar from "@/components/crm/CrmSavedViewsBar";
import {
  GRID_PREFS_KEY,
  leadStatusKinds,
  loadLeadGridPrefs,
  saveLeadGridPrefs,
  statusChipLabel,
  type GridDensity,
  type LeadGridPrefs,
} from "@/components/crm/leadGridStatus";
import { CRM_WORKSPACE, primaryEmail, type CrmRecord } from "@/components/crm/types";
import {
  fetchCrmLeadsGrid,
  patchCrmRecord,
  type CrmSavedView,
} from "@/lib/crm-api";

type UndoEntry = {
  id: string;
  field: string;
  previous: unknown;
  version?: number;
};

function primaryPhone(row: CrmRecord): string {
  const phones = row.phones;
  if (!Array.isArray(phones) || phones.length === 0) return "";
  const first = phones[0];
  if (typeof first === "string") return first;
  if (first && typeof first === "object") {
    const obj = first as { number?: string; phone?: string };
    return String(obj.number || obj.phone || "");
  }
  return "";
}

function densityToMui(density: GridDensity): "compact" | "standard" | "comfortable" {
  if (density === "compact") return "compact";
  if (density === "spacious") return "comfortable";
  return "standard";
}

export default function CrmLeadsDataGrid() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const prefsRef = React.useRef<LeadGridPrefs>(loadLeadGridPrefs());

  const [q, setQ] = React.useState("");
  const [stage, setStage] = React.useState("");
  const [source, setSource] = React.useState("");
  const [density, setDensity] = React.useState<GridDensity>(prefsRef.current.density || "comfortable");
  const [sortModel, setSortModel] = React.useState<GridSortModel>([
    {
      field: prefsRef.current.sort || "updated_at",
      sort: prefsRef.current.order || "desc",
    },
  ]);
  const [paginationModel, setPaginationModel] = React.useState<GridPaginationModel>({
    page: 0,
    pageSize: 50,
  });
  const [cursorStack, setCursorStack] = React.useState<(string | null)[]>([null]);
  const [columnVisibilityModel, setColumnVisibilityModel] = React.useState<GridColumnVisibilityModel>(
    prefsRef.current.columnVisibilityModel || {},
  );
  const [selection, setSelection] = React.useState<GridRowSelectionModel>({ type: "include", ids: new Set() });
  const [drawerLeadId, setDrawerLeadId] = React.useState<string | null>(null);
  const [activeViewId, setActiveViewId] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [undoStack, setUndoStack] = React.useState<UndoEntry[]>([]);

  const sortField = sortModel[0]?.field || "updated_at";
  const sortOrder = (sortModel[0]?.sort || "desc") as "asc" | "desc";
  const cursor = cursorStack[paginationModel.page] ?? null;

  const filter = React.useMemo(
    () => ({
      q: q || undefined,
      stage: stage || undefined,
      source: source || undefined,
      sort: sortField,
      order: sortOrder,
    }),
    [q, stage, source, sortField, sortOrder],
  );

  const list = useSWR(
    ["crm-leads-grid", CRM_WORKSPACE, filter, paginationModel.pageSize, cursor],
    () =>
      fetchCrmLeadsGrid(
        {
          ...filter,
          limit: paginationModel.pageSize,
          cursor: cursor || undefined,
          offset: cursor ? undefined : 0,
        },
        CRM_WORKSPACE,
      ),
  );

  const rows = React.useMemo(() => {
    return (list.data?.items ?? []).map((row) => ({
      ...row,
      email: primaryEmail(row),
      phone: primaryPhone(row),
      status_kinds: leadStatusKinds(row),
    }));
  }, [list.data?.items]);

  React.useEffect(() => {
    if (!list.data?.next_cursor) return;
    setCursorStack((prev) => {
      const next = [...prev];
      next[paginationModel.page + 1] = list.data?.next_cursor || null;
      return next;
    });
  }, [list.data?.next_cursor, paginationModel.page]);

  React.useEffect(() => {
    const prefs: LeadGridPrefs = {
      columnVisibilityModel,
      density,
      sort: sortField,
      order: sortOrder,
      columnWidths: prefsRef.current.columnWidths,
      columnOrder: prefsRef.current.columnOrder,
    };
    prefsRef.current = prefs;
    saveLeadGridPrefs(prefs);
  }, [columnVisibilityModel, density, sortField, sortOrder]);

  const persistWidth = (field: string, width: number) => {
    const widths = { ...(prefsRef.current.columnWidths || {}), [field]: width };
    prefsRef.current = { ...prefsRef.current, columnWidths: widths };
    saveLeadGridPrefs(prefsRef.current);
  };

  const width = (field: string, fallback: number) => prefsRef.current.columnWidths?.[field] ?? fallback;

  const columns = React.useMemo<GridColDef[]>(() => {
    const base: GridColDef[] = [
      {
        field: "status",
        headerName: "Status",
        width: width("status", 160),
        sortable: false,
        renderCell: (params) => (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
            {(params.row.status_kinds as string[]).slice(0, 3).map((kind) => (
              <Chip key={kind} size="small" label={statusChipLabel(kind as never)} />
            ))}
          </Stack>
        ),
      },
      {
        field: "company_name",
        headerName: "Company",
        width: width("company_name", 180),
        editable: true,
        renderCell: (params) => (
          <Link href={`/crm/leads/${params.row.id}`}>{String(params.value || "(no company)")}</Link>
        ),
      },
      { field: "name", headerName: "Contact", width: width("name", 140), editable: true },
      { field: "niche", headerName: "Niche", width: width("niche", 120), editable: true },
      { field: "locality", headerName: "Town/City", width: width("locality", 120), editable: true },
      { field: "website", headerName: "Website", width: width("website", 160), editable: true },
      { field: "email", headerName: "Email", width: width("email", 180), editable: true },
      { field: "phone", headerName: "Phone", width: width("phone", 130), editable: true },
      { field: "google_reviews", headerName: "Google Reviews", width: width("google_reviews", 120), editable: true },
      { field: "google_rating", headerName: "Google Rating", width: width("google_rating", 110), editable: true },
      { field: "google_maps_url", headerName: "Google Maps URL", width: width("google_maps_url", 160), editable: true },
      { field: "website_score", headerName: "Website Score", width: width("website_score", 110), editable: true },
      { field: "ranks_top3", headerName: "Ranks Top3?", width: width("ranks_top3", 110), editable: true },
      { field: "weakness", headerName: "Weakness", width: width("weakness", 140), editable: true },
      { field: "priority", headerName: "Priority", width: width("priority", 100), editable: true },
      { field: "stage", headerName: "Status / Stage", width: width("stage", 120), editable: true },
      { field: "source_captured_at", headerName: "Date Added", width: width("source_captured_at", 140), editable: true },
      { field: "notes", headerName: "Notes", width: width("notes", 180), editable: true },
      { field: "source", headerName: "Source", width: width("source", 110), editable: true },
      { field: "source_url", headerName: "Source URL", width: width("source_url", 160), editable: true },
      { field: "pipeline_stage", headerName: "Pipeline Stage", width: width("pipeline_stage", 130), editable: true },
      { field: "last_contacted_at", headerName: "Last Contact", width: width("last_contacted_at", 140), editable: true },
      { field: "last_reply_at", headerName: "Last Reply", width: width("last_reply_at", 140), editable: true },
      { field: "next_action_at", headerName: "Next Action", width: width("next_action_at", 140), editable: true },
      { field: "list_id", headerName: "Lists", width: width("list_id", 120), editable: true },
      { field: "campaign_id", headerName: "Campaigns", width: width("campaign_id", 120), editable: true },
      { field: "sequence_id", headerName: "Sequence", width: width("sequence_id", 120), editable: true },
      { field: "consent_status", headerName: "Consent", width: width("consent_status", 110), editable: true },
      { field: "suppression_reason", headerName: "Suppression", width: width("suppression_reason", 140), editable: true },
      { field: "owner_agent_id", headerName: "Owner Agent", width: width("owner_agent_id", 130), editable: true },
      {
        field: "actions",
        headerName: "History",
        width: 100,
        sortable: false,
        filterable: false,
        renderCell: (params) => (
          <Button size="small" onClick={() => setDrawerLeadId(String(params.row.id))} aria-label="Open provenance">
            Open
          </Button>
        ),
      },
    ];
    return base;
  }, []);

  const processRowUpdate = async (newRow: CrmRecord, oldRow: CrmRecord) => {
    setError(null);
    const changed: Record<string, unknown> = {};
    for (const key of Object.keys(newRow)) {
      if (["id", "status_kinds", "email", "phone", "version"].includes(key)) continue;
      if (newRow[key] !== oldRow[key]) changed[key] = newRow[key];
    }
    if (newRow.email !== oldRow.email && newRow.email !== primaryEmail(oldRow)) {
      changed.emails = [{ address: String(newRow.email || ""), primary: true }];
    }
    if (newRow.phone !== oldRow.phone && newRow.phone !== primaryPhone(oldRow)) {
      changed.phones = [{ number: String(newRow.phone || ""), primary: true }];
    }
    if (Object.keys(changed).length === 0) return oldRow;

    const field = Object.keys(changed)[0];
    setUndoStack((prev) => [
      ...prev.slice(-19),
      { id: oldRow.id, field, previous: oldRow[field], version: oldRow.version },
    ]);

    try {
      const result = await patchCrmRecord(
        "leads",
        oldRow.id,
        { ...changed, expected_version: oldRow.version },
        CRM_WORKSPACE,
      );
      if ((result as { blocked?: boolean }).blocked) {
        setError("Soft Wall blocked this stage change. Approve from Soft Wall, then retry.");
        throw new Error("soft_wall_blocked");
      }
      const lead = ((result as { lead?: CrmRecord }).lead || newRow) as CrmRecord;
      setMessage("Cell saved");
      await list.mutate();
      return {
        ...lead,
        email: primaryEmail(lead),
        phone: primaryPhone(lead),
        status_kinds: leadStatusKinds(lead),
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Save failed";
      if (msg.includes("409") || msg.includes("version_conflict") || msg.toLowerCase().includes("conflict")) {
        setError("Version conflict: another edit won. Reloading row.");
        await list.mutate();
      } else if (msg !== "soft_wall_blocked") {
        setError(msg);
      }
      throw err;
    }
  };

  const undoLast = async () => {
    const last = undoStack[undoStack.length - 1];
    if (!last) return;
    setUndoStack((prev) => prev.slice(0, -1));
    try {
      await patchCrmRecord(
        "leads",
        last.id,
        { [last.field]: last.previous, expected_version: undefined },
        CRM_WORKSPACE,
      );
      setMessage(`Undid edit on ${last.field}`);
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Undo failed");
    }
  };

  const selectedRows = rows.filter((r) => selection.ids.has(r.id));
  const viewConfig = {
    filters: filter,
    density,
    columnVisibilityModel,
    sort: sortField,
    order: sortOrder,
  };

  const applyView = (view: CrmSavedView) => {
    setActiveViewId(view.id);
    const cfg = view.config || {};
    const filters = (cfg.filters || {}) as Record<string, string>;
    setQ(String(filters.q || ""));
    setStage(String(filters.stage || ""));
    setSource(String(filters.source || ""));
    if (cfg.density) setDensity(cfg.density as GridDensity);
    if (cfg.columnVisibilityModel) setColumnVisibilityModel(cfg.columnVisibilityModel as GridColumnVisibilityModel);
    if (cfg.sort) {
      setSortModel([{ field: String(cfg.sort), sort: (cfg.order as "asc" | "desc") || "desc" }]);
    }
    setPaginationModel((p) => ({ ...p, page: 0 }));
    setCursorStack([null]);
  };

  if (isMobile) {
    return (
      <Stack spacing={1.5}>
        <Typography variant="h5">Leads</Typography>
        <TextField
          size="small"
          label="Search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          fullWidth
          inputProps={{ "aria-label": "Search leads" }}
        />
        <CrmLeadsImportExportToolbar workspaceId={CRM_WORKSPACE} filter={filter} onImported={() => void list.mutate()} />
        {(rows || []).map((row) => (
          <Card key={row.id} variant="outlined">
            <CardActionArea component={Link} href={`/crm/leads/${row.id}`}>
              <CardContent>
                <Typography fontWeight={600}>{String(row.company_name || row.name || row.id)}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {primaryEmail(row) || "No email"} · {String(row.stage || "")}
                </Typography>
                <Stack direction="row" spacing={0.5} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                  {leadStatusKinds(row).slice(0, 3).map((kind) => (
                    <Chip key={kind} size="small" label={statusChipLabel(kind)} />
                  ))}
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Stack>
    );
  }

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" useFlexGap>
        <Box>
          <Typography variant="h5">Leads</Typography>
          <Typography variant="body2" color="text.secondary">
            Spreadsheet CRM workspace. Inline edits hit real APIs; Soft Wall gates high-risk stage changes.
          </Typography>
        </Box>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={density}
          onChange={(_, v) => v && setDensity(v)}
          aria-label="Grid density"
        >
          <ToggleButton value="compact">Compact</ToggleButton>
          <ToggleButton value="comfortable">Comfortable</ToggleButton>
          <ToggleButton value="spacious">Spacious</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <TextField size="small" label="Search" value={q} onChange={(e) => setQ(e.target.value)} inputProps={{ "aria-label": "Search leads" }} />
        <TextField size="small" label="Stage" value={stage} onChange={(e) => setStage(e.target.value)} />
        <TextField size="small" label="Source" value={source} onChange={(e) => setSource(e.target.value)} />
        <Button
          size="small"
          onClick={() => {
            setPaginationModel((p) => ({ ...p, page: 0 }));
            setCursorStack([null]);
            void list.mutate();
          }}
        >
          Apply filters
        </Button>
        <Button size="small" disabled={!undoStack.length} onClick={() => void undoLast()}>
          Undo edit
        </Button>
      </Stack>

      <CrmSavedViewsBar
        workspaceId={CRM_WORKSPACE}
        activeViewId={activeViewId}
        onApply={applyView}
        currentConfig={viewConfig}
      />
      <CrmLeadsImportExportToolbar workspaceId={CRM_WORKSPACE} filter={filter} onImported={() => void list.mutate()} />
      <CrmLeadsBulkBar
        selected={selectedRows}
        workspaceId={CRM_WORKSPACE}
        filter={filter}
        onDone={() => void list.mutate()}
      />

      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {message ? <Alert severity="success" onClose={() => setMessage(null)}>{message}</Alert> : null}

      <Box sx={{ height: 640, width: "100%" }} data-prefs-key={GRID_PREFS_KEY}>
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(row) => row.id}
          checkboxSelection
          disableRowSelectionOnClick
          density={densityToMui(density)}
          loading={list.isLoading}
          rowCount={list.data?.total ?? list.data?.count ?? 0}
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={(model) => {
            if (model.page < paginationModel.page) {
              setCursorStack((prev) => prev.slice(0, model.page + 1));
            }
            setPaginationModel(model);
          }}
          sortModel={sortModel}
          onSortModelChange={(model) => {
            setSortModel(model);
            setPaginationModel((p) => ({ ...p, page: 0 }));
            setCursorStack([null]);
          }}
          pageSizeOptions={[25, 50, 100]}
          columnVisibilityModel={columnVisibilityModel}
          onColumnVisibilityModelChange={setColumnVisibilityModel}
          onColumnWidthChange={(params) => persistWidth(params.colDef.field, params.width)}
          rowSelectionModel={selection}
          onRowSelectionModelChange={setSelection}
          processRowUpdate={processRowUpdate}
          onProcessRowUpdateError={() => undefined}
          sx={{
            "& .MuiDataGrid-columnHeaders": { position: "sticky", top: 0, zIndex: 1 },
            // Community DataGrid has no column pinning; sticky left approximates frozen cols.
            "& .MuiDataGrid-cell[data-field='company_name'], & .MuiDataGrid-columnHeader[data-field='company_name']": {
              position: "sticky",
              left: 48,
              zIndex: 2,
              backgroundColor: "background.paper",
            },
            "& .MuiDataGrid-cell[data-field='name'], & .MuiDataGrid-columnHeader[data-field='name']": {
              position: "sticky",
              left: 228,
              zIndex: 2,
              backgroundColor: "background.paper",
            },
          }}
        />
      </Box>

      <CrmLeadProvenanceDrawer
        leadId={drawerLeadId}
        open={Boolean(drawerLeadId)}
        onClose={() => setDrawerLeadId(null)}
        workspaceId={CRM_WORKSPACE}
      />
    </Stack>
  );
}
