"""Shim: redirect agent.* imports to keprix.agent.*"""
import os as _os
__path__ = [_os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "keprix", "agent")]
