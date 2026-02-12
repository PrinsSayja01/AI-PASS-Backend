"""
Small compatibility wrapper.

Different versions of this repo used different files for require_access.
This wrapper tries multiple imports so other modules can always do:

    from api.deps import require_access
"""
from typing import Dict, Any
from fastapi import Depends  # not required but keeps typing clean

def _import_require_access():
    # Try common locations in this repo
    candidates = [
        ("api.auth_deps", "require_access"),
        ("api.auth", "require_access"),
        ("api.security_deps", "require_access"),
    ]
    last_err = None
    for mod, name in candidates:
        try:
            m = __import__(mod, fromlist=[name])
            return getattr(m, name)
        except Exception as e:
            last_err = e
    raise ImportError(f"Could not import require_access from known locations. Last error: {last_err}")

require_access = _import_require_access()
