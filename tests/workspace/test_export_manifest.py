from __future__ import annotations

import io
import json
import zipfile

from keprix.document_vault.channel.scoped_export import build_scoped_zip


def test_scoped_export_contains_manifest() -> None:
    filename, data, count = build_scoped_zip("workspace-with-no-data")
    assert filename.startswith("keprix-workspace-with-no-data")
    assert count == 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["workspace_id"] == "workspace-with-no-data"
