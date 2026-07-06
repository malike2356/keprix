"""Memory provider swap tests."""

import pytest

from keprix.kernel.memory_provider import (
    FileIndexKernelMemory,
    InMemoryKernelMemory,
    SqliteKernelMemory,
    get_memory_backend,
    set_memory_backend,
)


@pytest.mark.asyncio
async def test_memory_provider_can_be_swapped_in_tests(tmp_path) -> None:
    set_memory_backend(InMemoryKernelMemory())
    backend = get_memory_backend()
    await backend.remember("note", "kernel memory works")
    rows = await backend.recall("kernel")
    assert rows[0].content == "kernel memory works"

    sqlite_backend = SqliteKernelMemory(tmp_path / "memory.sqlite")
    set_memory_backend(sqlite_backend)
    await get_memory_backend().remember("sql", "sqlite provider")
    recalled = await get_memory_backend().recall("sqlite")
    assert recalled[0].key == "sql"

    file_backend = FileIndexKernelMemory(tmp_path / "file-index")
    set_memory_backend(file_backend)
    await get_memory_backend().remember("file", "file index provider")
    recalled = await get_memory_backend().recall("file")
    assert recalled[0].content == "file index provider"
