"""Utilities for dependency management across launchers and UI."""

from __future__ import annotations

import sys
from typing import Final, Tuple

LEGACY_REMBG_SPEC = "rembg==2.0.50"
CURRENT_REMBG_SPEC = "rembg==2.0.67"


def rembg_requirement() -> Tuple[str | None, str | None]:
    """Return the pip requirement string for ``rembg`` or an error message.

    The rembg project only publishes wheels for specific Python versions.  Older
    interpreters (3.7 and below) and bleeding-edge versions (3.14+) currently
    have no compatible builds, which would make ``pip install rembg`` fail with
    a "No matching distribution" error.  This helper selects a compatible
    version for supported interpreters and surfaces a friendly message when the
    environment is outside the supported range.
    """

    version: Final[tuple[int, int]] = sys.version_info[:2]

    if version < (3, 8):
        return None, (
            "rembg requires Python 3.8 or newer. Upgrade Python to enable "
            "background removal support."
        )
    if version < (3, 12):
        return LEGACY_REMBG_SPEC, None
    if version < (3, 14):
        return CURRENT_REMBG_SPEC, None
    return None, (
        "rembg is not yet available for Python 3.14+. Install Python 3.12 or "
        "3.11 to use background removal."
    )

