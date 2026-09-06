"""Typed, policy-controlled OSINT investigation primitives."""

from .entity import Entity
from .orchestrator import investigate

__all__ = ["Entity", "investigate"]
