"""Shim: redirect plugins.* imports to keprix.plugins.*"""
import os as _os
__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "plugins")]
