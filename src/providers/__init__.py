"""Shim: redirect providers.* imports to keprix.providers.*"""
import os as _os
__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "providers")]
