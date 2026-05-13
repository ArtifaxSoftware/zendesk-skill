"""Cross-platform helpers for restricting file access to the current owner.

POSIX uses traditional ``0o600`` mode bits. Windows ignores POSIX modes; this
module instead disables ACL inheritance and grants the current user full
control via the built-in ``icacls`` utility (no extra dependencies).

Files under ``%USERPROFILE%`` already inherit user-only NTFS ACLs from the
profile directory, so this hardening is defence in depth — it removes the
dependency on parent-directory configuration and matches the explicit
``0o600`` intent already present on POSIX.
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path


def restrict_to_owner(path: Path) -> None:
    """Restrict *path* so only the current user can read or write it.

    POSIX: ``chmod 0o600``.
    Windows: strip ACL inheritance and grant the current user full control via
    ``icacls``. Silently no-ops if the call fails — the file is still protected
    by inherited ACLs from ``%USERPROFILE%`` in that case.
    """
    if sys.platform == "win32":
        try:
            user = getpass.getuser()
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                capture_output=True,
                check=False,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
    else:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def is_owner_restricted(path: Path) -> bool:
    """Return True if *path* is restricted to the current user only.

    POSIX: mode bits equal ``0o600``.
    Windows: ``icacls`` reports the current user with full control. We do not
    try to validate the absence of every other principal because ``icacls``
    output is localised; a positive grant for the current user after
    ``/inheritance:r`` is sufficient to confirm ``restrict_to_owner`` ran.
    """
    if not path.exists():
        return False
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["icacls", str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
        if result.returncode != 0:
            return False
        return f"{getpass.getuser()}:(F)" in result.stdout
    return path.stat().st_mode & 0o777 == 0o600
