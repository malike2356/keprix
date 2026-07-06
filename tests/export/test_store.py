"""Export store persistence tests."""

from __future__ import annotations

from keprix.export.store import ExportStore


def test_export_store_save_and_resolve(tmp_path) -> None:
    store = ExportStore(base_dir=tmp_path)
    record = store.save(
        title="Compliance Report",
        content=b"%PDF-1.4 test",
        mime="application/pdf",
        format_returned="pdf",
    )
    path = store.resolve_path(record.file_id)
    assert path is not None
    assert path.exists()
    assert store.get(record.file_id) is not None
