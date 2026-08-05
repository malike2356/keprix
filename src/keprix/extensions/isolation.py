"""Product isolation enforcement: prevent cross-product imports at startup."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Known product package names. Keep in sync with the extension registry.
_KNOWN_PRODUCTS: set[str] = {"abbis", "petraclus", "fleetz", "nhs_keprix"}


@dataclass
class IsolationViolation:
    importer: str      # module doing the bad import
    imported: str      # forbidden module being imported
    reason: str = ""


class IsolationEnforcer:
    """Check that product packages do not import each other.

    This is enforced at startup by scanning the import graph of loaded
    modules. It is advisory in tests (raises warnings) and can be set to
    strict mode for CI.

    Rule: a module whose dotted name starts with ``product_a.`` MUST NOT
    import from any module whose dotted name starts with ``product_b.``
    where product_a != product_b and both are in the known product set.

    Usage::

        enforcer = IsolationEnforcer(products={"abbis", "petraclus"})
        violations = enforcer.scan()
        if violations:
            raise RuntimeError(enforcer.format_violations(violations))
    """

    def __init__(self, products: set[str] | None = None) -> None:
        self._products = products or _KNOWN_PRODUCTS

    def scan(self) -> list[IsolationViolation]:
        """Scan currently loaded modules for cross-product imports."""
        violations: list[IsolationViolation] = []
        for mod_name, mod in list(sys.modules.items()):
            if mod is None:
                continue
            importer_product = self._product_of(mod_name)
            if not importer_product:
                continue
            # Walk the module's __dict__ for references to other product modules
            try:
                for attr_val in vars(mod).values():
                    attr_mod = getattr(attr_val, "__module__", None) or ""
                    imported_product = self._product_of(attr_mod)
                    if imported_product and imported_product != importer_product:
                        violations.append(IsolationViolation(
                            importer=mod_name,
                            imported=attr_mod,
                            reason=(
                                f"Product {importer_product!r} imports from "
                                f"{imported_product!r}"
                            ),
                        ))
            except Exception:
                pass
        return violations

    def _product_of(self, module_name: str) -> str | None:
        """Return the product name a module belongs to, or None."""
        for product in self._products:
            if module_name == product or module_name.startswith(f"{product}."):
                return product
        return None

    @staticmethod
    def format_violations(violations: list[IsolationViolation]) -> str:
        lines = ["Cross-product import violations detected:"]
        for v in violations:
            lines.append(f"  {v.importer} -> {v.imported}: {v.reason}")
        return "\n".join(lines)

    def assert_isolated(self, strict: bool = False) -> None:
        """Run isolation check. Warns in non-strict mode, raises in strict."""
        violations = self.scan()
        if violations:
            msg = self.format_violations(violations)
            if strict:
                raise RuntimeError(msg)
            logger.warning(msg)
