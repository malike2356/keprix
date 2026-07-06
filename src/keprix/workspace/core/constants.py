"""Workspace constants."""

from __future__ import annotations

import os

from keprix.auth.config import data_dir

PRODUCT_NAME = "keprix"
WORKSPACE_ROOT = os.path.join(data_dir(), "workspace")
DRAFT_TTL_SECONDS = 60 * 60 * 24
