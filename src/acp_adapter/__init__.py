"""Shim: redirect acp_adapter.* imports to keprix.acp_adapter.*"""
import os as _os
__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "acp_adapter")]
