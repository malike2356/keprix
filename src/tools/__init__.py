"""Shim: redirect tools.* imports to keprix.tools.*"""
import os as _os
__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "tools")]
