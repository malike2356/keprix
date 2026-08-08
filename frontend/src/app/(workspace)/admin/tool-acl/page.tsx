"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  type ActorType,
  checkResourceAccess,
  checkToolAccess,
  fetchAclAudit,
  fetchResourceCatalog,
  getProductAcl,
  listAclProducts,
  listResourceGrants,
  recordBroadGrant,
  revokeResourceGrant,
  upsertResourceGrant,
} from "@/lib/tool-acl-api";

const ACTOR_TYPES: ActorType[] = ["agent", "api_token", "user", "workspace", "product"];

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

export default function ToolAclAdminPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [tab, setTab] = React.useState(0);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Tool ACL" description="Product and resource access control." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Tool ACL" description="Product and resource access control." />
        <Alert severity="error">
          Admin role required. Your role ({user?.role || "unknown"}) cannot manage tool ACL. Ask an
          owner or admin, or use the API only if you already have elevated credentials.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Tool ACL"
        description="Grant and revoke product tool access and resource-scoped grants. Mutation-generated tools stay at /admin/tools."
        breadcrumbs={[
          { label: "Admin", href: "/control-center" },
          { label: "Tool ACL" },
        ]}
        actions={
          <Button component={NextLink} href="/admin/tools" variant="outlined" size="small">
            Generated tools
          </Button>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Tabs value={tab} onChange={(_, v: number) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Products" />
        <Tab label="Resource grants" />
        <Tab label="Check playground" />
        <Tab label="Audit" />
      </Tabs>

      {tab === 0 ? (
        <ProductAclPanel onError={setError} />
      ) : null}
      {tab === 1 ? (
        <ResourceGrantsPanel
          onError={setError}
          onMessage={setMessage}
        />
      ) : null}
      {tab === 2 ? <CheckPlaygroundPanel onError={setError} /> : null}
      {tab === 3 ? <AuditPanel onError={setError} /> : null}
    </Box>
  );
}

function ProductAclPanel({ onError }: { onError: (msg: string | null) => void }) {
  const { data, error, isLoading } = useSWR("acl-products", listAclProducts);
  const [selected, setSelected] = React.useState<string>("");

  React.useEffect(() => {
    if (!selected && data?.products?.length) {
      setSelected(data.products[0] || data.base_product || "");
    }
  }, [data, selected]);

  const detailKey = selected ? `acl-product-${selected}` : null;
  const {
    data: detail,
    error: detailError,
    isLoading: detailLoading,
  } = useSWR(detailKey, () => getProductAcl(selected));

  React.useEffect(() => {
    if (error) onError(error instanceof Error ? error.message : "Failed to load products");
    else if (detailError) onError(detailError instanceof Error ? detailError.message : "Failed to load product");
    else onError(null);
  }, [error, detailError, onError]);

  if (isLoading) return <SkeletonList rows={3} rowHeight={40} />;

  if (!data?.products?.length) {
    return (
      <EmptyState
        title="No products registered in ACL"
        description="The ACL store has no product entries yet. Base product may still apply at runtime."
      />
    );
  }

  return (
    <Stack spacing={2}>
      <FormControl size="small" sx={{ maxWidth: 360 }}>
        <InputLabel id="acl-product-label">Product</InputLabel>
        <Select
          labelId="acl-product-label"
          label="Product"
          value={selected}
          onChange={(e) => setSelected(String(e.target.value))}
        >
          {data.products.map((id) => (
            <MenuItem key={id} value={id}>
              {id}
              {id === data.base_product ? " (base)" : ""}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {detailLoading ? <SkeletonTable rows={4} columns={2} /> : null}

      {detail ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {detail.product_id}
            </Typography>
            {detail.is_base_product ? <Chip size="small" label="base" color="info" /> : null}
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Product ACL is read-only in this console. Use config / code registration to change
            allowed and denied tool lists. Use the check playground to preview decisions.
          </Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Allowed tools
              </Typography>
              {detail.allowed_tools.length === 0 ? (
                <Typography variant="body2">None</Typography>
              ) : (
                <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mt: 0.5 }}>
                  {detail.allowed_tools.map((t) => (
                    <Chip key={t} size="small" label={t} variant="outlined" color="success" />
                  ))}
                </Stack>
              )}
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Denied tools
              </Typography>
              {detail.denied_tools.length === 0 ? (
                <Typography variant="body2">None</Typography>
              ) : (
                <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mt: 0.5 }}>
                  {detail.denied_tools.map((t) => (
                    <Chip key={t} size="small" label={t} variant="outlined" color="error" />
                  ))}
                </Stack>
              )}
            </Box>
          </Stack>
        </Paper>
      ) : null}
    </Stack>
  );
}

function ResourceGrantsPanel({
  onError,
  onMessage,
}: {
  onError: (msg: string | null) => void;
  onMessage: (msg: string | null) => void;
}) {
  const [actorType, setActorType] = React.useState<ActorType>("agent");
  const [actorId, setActorId] = React.useState("");
  const [loadedActor, setLoadedActor] = React.useState<{ type: ActorType; id: string } | null>(null);
  const [service, setService] = React.useState("");
  const [kind, setKind] = React.useState("");
  const [resourceId, setResourceId] = React.useState("");
  const [actions, setActions] = React.useState("read,write");
  const [broadNote, setBroadNote] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [confirmBroad, setConfirmBroad] = React.useState(false);
  const [confirmRevoke, setConfirmRevoke] = React.useState<{
    service: string;
    kind: string;
    resource_id: string;
  } | null>(null);

  const catalog = useSWR("acl-resource-catalog", fetchResourceCatalog);
  const grantsKey = loadedActor
    ? `acl-grants-${loadedActor.type}-${loadedActor.id}`
    : null;
  const grants = useSWR(grantsKey, () =>
    listResourceGrants(loadedActor!.type, loadedActor!.id),
  );

  const services = catalog.data?.services ?? [];
  const selectedService = services.find((s) => s.service === service);
  const kinds = (selectedService?.kinds || [])
    .map((k) => (typeof k === "string" ? k : k.kind))
    .filter(Boolean);

  const loadGrants = () => {
    const id = actorId.trim();
    if (!id) {
      onError("Actor ID is required");
      return;
    }
    onError(null);
    setLoadedActor({ type: actorType, id });
  };

  const saveGrant = async () => {
    if (!loadedActor) {
      onError("Load an actor first");
      return;
    }
    if (!service.trim() || !kind.trim() || !resourceId.trim()) {
      onError("Service, kind, and resource ID are required");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      await upsertResourceGrant({
        actor_type: loadedActor.type,
        actor_id: loadedActor.id,
        service: service.trim(),
        kind: kind.trim(),
        resource_id: resourceId.trim(),
        actions: actions
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
      onMessage(`Grant saved for ${resourceId.trim()}`);
      setResourceId("");
      await grants.mutate();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const doRevoke = async () => {
    if (!loadedActor || !confirmRevoke) return;
    setBusy(true);
    onError(null);
    try {
      const result = await revokeResourceGrant({
        actor_type: loadedActor.type,
        actor_id: loadedActor.id,
        ...confirmRevoke,
      });
      onMessage(result.revoked ? "Grant revoked" : "No matching grant found");
      setConfirmRevoke(null);
      await grants.mutate();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  };

  const doBroad = async () => {
    if (!loadedActor || !service.trim()) {
      onError("Load an actor and choose a service first");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      await recordBroadGrant({
        actor_type: loadedActor.type,
        actor_id: loadedActor.id,
        service: service.trim(),
        note: broadNote.trim() || undefined,
      });
      onMessage(`Broad grant recorded for ${service.trim()}`);
      setConfirmBroad(false);
      await grants.mutate();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Broad grant failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
          Actor
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="actor-type-label">Actor type</InputLabel>
            <Select
              labelId="actor-type-label"
              label="Actor type"
              value={actorType}
              onChange={(e) => setActorType(e.target.value as ActorType)}
            >
              {ACTOR_TYPES.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Actor ID"
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            sx={{ flex: 1 }}
          />
          <Button variant="contained" onClick={loadGrants} disabled={busy}>
            Load grants
          </Button>
        </Stack>
      </Paper>

      {!loadedActor ? (
        <EmptyState
          title="No actor loaded"
          description="Enter an actor type and ID, then load grants. Empty grants for a service mean unrestricted (legacy broad access)."
        />
      ) : null}

      {grants.isLoading ? <SkeletonTable rows={4} columns={5} /> : null}
      {grants.error ? (
        <Alert severity="error">
          {grants.error instanceof Error ? grants.error.message : "Could not load grants"}
        </Alert>
      ) : null}

      {grants.data ? (
        <>
          <Typography variant="body2" color="text.secondary">
            {grants.data.note}
          </Typography>
          <Paper variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Service</TableCell>
                  <TableCell>Kind</TableCell>
                  <TableCell>Resource</TableCell>
                  <TableCell>Actions</TableCell>
                  <TableCell align="right"> </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {grants.data.grants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                        No exact grants for this actor. Access is unrestricted until you add grants.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  grants.data.grants.map((g) => (
                    <TableRow key={`${g.service}-${g.kind}-${g.resource_id}`}>
                      <TableCell>{g.service}</TableCell>
                      <TableCell>{g.kind}</TableCell>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 13 }}>
                        {g.resource_id}
                      </TableCell>
                      <TableCell>{(g.actions || []).join(", ")}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          color="error"
                          disabled={busy}
                          onClick={() =>
                            setConfirmRevoke({
                              service: g.service,
                              kind: g.kind,
                              resource_id: g.resource_id,
                            })
                          }
                        >
                          Revoke
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Paper>

          {grants.data.broad_grants?.length ? (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Recorded broad grants
              </Typography>
              <StructuredDataView value={grants.data.broad_grants} />
            </Paper>
          ) : null}

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
              Add exact grant
            </Typography>
            <Stack spacing={1.5}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <FormControl size="small" sx={{ minWidth: 160, flex: 1 }}>
                  <InputLabel id="svc-label">Service</InputLabel>
                  <Select
                    labelId="svc-label"
                    label="Service"
                    value={service}
                    onChange={(e) => {
                      setService(String(e.target.value));
                      setKind("");
                    }}
                  >
                    {(services.length ? services : [{ service: "custom" }]).map((s) => (
                      <MenuItem key={String(s.service)} value={String(s.service)}>
                        {String(s.service)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {kinds.length ? (
                  <FormControl size="small" sx={{ minWidth: 140, flex: 1 }}>
                    <InputLabel id="kind-label">Kind</InputLabel>
                    <Select
                      labelId="kind-label"
                      label="Kind"
                      value={kind}
                      onChange={(e) => setKind(String(e.target.value))}
                    >
                      {kinds.map((k) => (
                        <MenuItem key={k} value={k}>
                          {k}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ) : (
                  <TextField
                    size="small"
                    label="Kind"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                    sx={{ flex: 1 }}
                  />
                )}
                <TextField
                  size="small"
                  label="Resource ID"
                  value={resourceId}
                  onChange={(e) => setResourceId(e.target.value)}
                  sx={{ flex: 1.5 }}
                />
              </Stack>
              <TextField
                size="small"
                label="Actions (comma-separated)"
                value={actions}
                onChange={(e) => setActions(e.target.value)}
              />
              <Stack direction="row" spacing={1}>
                <Button variant="contained" disabled={busy} onClick={() => void saveGrant()}>
                  Save grant
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  disabled={busy || !service.trim()}
                  onClick={() => setConfirmBroad(true)}
                >
                  Record broad grant
                </Button>
              </Stack>
              <TextField
                size="small"
                label="Broad grant note (optional)"
                value={broadNote}
                onChange={(e) => setBroadNote(e.target.value)}
              />
            </Stack>
          </Paper>
        </>
      ) : null}

      <Dialog open={Boolean(confirmRevoke)} onClose={() => setConfirmRevoke(null)}>
        <DialogTitle>Revoke resource grant?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Revoke {confirmRevoke?.service}/{confirmRevoke?.kind}/{confirmRevoke?.resource_id} for{" "}
            {loadedActor?.type}:{loadedActor?.id}? This is a destructive ACL change.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmRevoke(null)}>Cancel</Button>
          <Button color="error" variant="contained" disabled={busy} onClick={() => void doRevoke()}>
            Revoke
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={confirmBroad} onClose={() => setConfirmBroad(false)}>
        <DialogTitle>Record broad (unrestricted) grant?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Broad grants mark legacy unrestricted access for service &quot;{service}&quot;. Prefer
            exact resource grants when possible. Confirm to record visibility while narrowing.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmBroad(false)}>Cancel</Button>
          <Button color="warning" variant="contained" disabled={busy} onClick={() => void doBroad()}>
            Record broad grant
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

function CheckPlaygroundPanel({ onError }: { onError: (msg: string | null) => void }) {
  const { data: products } = useSWR("acl-products", listAclProducts);
  const [productId, setProductId] = React.useState("");
  const [toolName, setToolName] = React.useState("");
  const [toolResult, setToolResult] = React.useState<Record<string, unknown> | null>(null);
  const [resTool, setResTool] = React.useState("");
  const [resArgs, setResArgs] = React.useState("{}");
  const [actorType, setActorType] = React.useState<ActorType | "">("");
  const [actorId, setActorId] = React.useState("");
  const [resResult, setResResult] = React.useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!productId && products?.base_product) setProductId(products.base_product);
  }, [products, productId]);

  const runToolCheck = async () => {
    setBusy(true);
    onError(null);
    try {
      const result = await checkToolAccess(productId.trim(), toolName.trim());
      setToolResult(result as unknown as Record<string, unknown>);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Check failed");
    } finally {
      setBusy(false);
    }
  };

  const runResourceCheck = async () => {
    setBusy(true);
    onError(null);
    try {
      let args: Record<string, unknown> = {};
      try {
        args = JSON.parse(resArgs || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("Args must be valid JSON");
      }
      const result = await checkResourceAccess({
        tool_name: resTool.trim(),
        args,
        actor_type: actorType || undefined,
        actor_id: actorId.trim() || undefined,
      });
      setResResult(result as unknown as Record<string, unknown>);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Resource check failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
          Product tool check
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 1 }}>
          <TextField
            size="small"
            label="Product ID"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            sx={{ flex: 1 }}
          />
          <TextField
            size="small"
            label="Tool name"
            value={toolName}
            onChange={(e) => setToolName(e.target.value)}
            sx={{ flex: 1 }}
          />
          <Button
            variant="contained"
            disabled={busy || !productId.trim() || !toolName.trim()}
            onClick={() => void runToolCheck()}
          >
            Check
          </Button>
        </Stack>
        {toolResult ? <StructuredDataView value={toolResult} /> : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
          Resource ACL check
        </Typography>
        <Stack spacing={1}>
          <TextField
            size="small"
            label="Tool name"
            value={resTool}
            onChange={(e) => setResTool(e.target.value)}
          />
          <TextField
            size="small"
            label="Args (JSON)"
            value={resArgs}
            onChange={(e) => setResArgs(e.target.value)}
            multiline
            minRows={3}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="chk-actor-type">Actor type</InputLabel>
              <Select
                labelId="chk-actor-type"
                label="Actor type"
                value={actorType}
                onChange={(e) => setActorType(e.target.value as ActorType | "")}
              >
                <MenuItem value="">(none)</MenuItem>
                {ACTOR_TYPES.map((t) => (
                  <MenuItem key={t} value={t}>
                    {t}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Actor ID"
              value={actorId}
              onChange={(e) => setActorId(e.target.value)}
              sx={{ flex: 1 }}
            />
            <Button
              variant="contained"
              disabled={busy || !resTool.trim()}
              onClick={() => void runResourceCheck()}
            >
              Check resource
            </Button>
          </Stack>
          {resResult ? <StructuredDataView value={resResult} /> : null}
        </Stack>
      </Paper>
    </Stack>
  );
}

function AuditPanel({ onError }: { onError: (msg: string | null) => void }) {
  const [productFilter, setProductFilter] = React.useState("");
  const [limit, setLimit] = React.useState(50);
  const key = `acl-audit-${limit}-${productFilter}`;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAclAudit(limit, productFilter.trim() || undefined),
  );

  React.useEffect(() => {
    if (error) onError(error instanceof Error ? error.message : "Audit load failed");
    else onError(null);
  }, [error, onError]);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
        <TextField
          size="small"
          label="Filter product ID"
          value={productFilter}
          onChange={(e) => setProductFilter(e.target.value)}
          sx={{ flex: 1 }}
        />
        <TextField
          size="small"
          type="number"
          label="Limit"
          value={limit}
          onChange={(e) => setLimit(Math.min(500, Math.max(1, Number(e.target.value) || 50)))}
          sx={{ width: 100 }}
        />
        <Button variant="outlined" onClick={() => void mutate()}>
          Refresh
        </Button>
      </Stack>

      {isLoading ? <SkeletonTable rows={6} columns={4} /> : null}

      {!isLoading && data && data.entries.length === 0 ? (
        <EmptyState
          title="No ACL audit entries"
          description="Decisions appear here as tools are checked against product and resource ACL."
        />
      ) : null}

      {data && data.entries.length > 0 ? (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Product</TableCell>
                <TableCell>Tool</TableCell>
                <TableCell>Decision</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[...data.entries].reverse().map((entry, i) => (
                <TableRow key={i}>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {String(entry.ts || entry.timestamp || entry.at || "-")}
                  </TableCell>
                  <TableCell>{String(entry.product_id || "-")}</TableCell>
                  <TableCell sx={{ fontFamily: "monospace", fontSize: 13 }}>
                    {String(entry.tool_name || entry.tool || "-")}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={String(entry.decision || entry.result || "-")}
                      color={
                        String(entry.decision || "").toLowerCase().includes("allow")
                          ? "success"
                          : String(entry.decision || "").toLowerCase().includes("deny")
                            ? "error"
                            : "default"
                      }
                      variant="outlined"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ) : null}
    </Stack>
  );
}
