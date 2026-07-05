"""Shim: redirect keprix_cli.* imports to keprix.keprix_cli.*"""
import os as _os

__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "keprix_cli")]

# Re-export package-level symbols so `from keprix_cli import __version__` works.
from keprix.keprix_cli import __version__, __release_date__  # noqa: F401
