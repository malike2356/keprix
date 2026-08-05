"""IsolationViolation: raised when a query escapes its product namespace."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class IsolationViolation(Exception):
    """Raised when a query attempts to access data outside its product namespace.

    The IsolationMiddleware converts this to HTTP 403.
    """

    def __init__(
        self,
        message: str,
        product_id: str = "",
        workspace_id: str = "",
        table: str = "",
    ) -> None:
        super().__init__(message)
        self.product_id = product_id
        self.workspace_id = workspace_id
        self.table = table
        logger.critical(
            "ISOLATION VIOLATION: product=%s workspace=%s table=%s: %s",
            product_id or "?",
            workspace_id or "?",
            table or "?",
            message,
        )
