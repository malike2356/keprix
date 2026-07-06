"""Kernel test fixtures."""

from __future__ import annotations

import pytest

from keprix.kernel.function_contract import clear_invocation_traces
from keprix.kernel.memory_provider import InMemoryKernelMemory, set_memory_backend


@pytest.fixture(autouse=True)
def kernel_test_isolation() -> None:
    clear_invocation_traces()
    set_memory_backend(InMemoryKernelMemory())
