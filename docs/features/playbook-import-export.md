# Playbook import and export

Studio can import existing playbook YAML and best-effort n8n workflow JSON, then export a portable Keprix bundle.

## n8n import

Use **Import n8n** in Studio or call:

```http
POST /api/playbooks/studio/import/n8n
```

Unsupported nodes are skipped with warnings. This is a bridge, not n8n parity, and no n8n Vue editor code is copied.

## YAML import

Use **Import YAML** in Studio or call:

```http
POST /api/playbooks/studio/import/yaml
```

The API validates with the playbook compiler and decompiles YAML into canvas nodes with generated layout.

## Run overlay

From a playbook run detail page, choose **View on canvas**. Studio opens read-only with `?run={run_id}` and maps timeline events to node status colors: pending, running, completed, failed, and waiting approval.

## Export bundle

```http
GET /api/playbooks/studio/{id}/export
```

The zip contains `{id}.yaml`, `{id}.layout.json`, and `README.txt`. Keprix does not export KNIME `.knwf` files.
