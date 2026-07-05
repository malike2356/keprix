"""Shim: redirect keprix_cli.* imports to keprix.keprix_cli.*"""
import os as _os

__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "keprix_cli")]
