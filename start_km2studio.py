"""One-click launcher for KM2 Image Studio with dependency bootstrapping."""
from __future__ import annotations

import subprocess
import sys
from importlib import import_module
from typing import Iterable

from dependency_utils import rembg_requirement

REQUIRED_IMPORTS = {
    "PIL": "pillow",
    "rembg": "rembg",
    "tkinterdnd2": "tkinterdnd2",
}


def _missing_packages() -> list[str]:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_IMPORTS.items():
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            if package_name == "rembg":
                requirement, error = rembg_requirement()
                if requirement is None:
                    print(f"⚠️ {error}")
                else:
                    missing.append(requirement)
            else:
                missing.append(package_name)
    return missing


def _install(packages: Iterable[str]) -> None:
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    print("Installing missing packages:", " ".join(packages))
    subprocess.check_call(cmd)


def _launch() -> None:
    # Import lazily so dependency installation happens first
    from km2_launcher import main as launch_main

    launch_main()


def main() -> None:
    try:
        missing = _missing_packages()
        if missing:
            _install(missing)
    except subprocess.CalledProcessError as exc:
        print("\n⚠️ Could not install dependencies automatically.")
        print("   Please run: python -m pip install -r requirements.txt")
        print("   Error:", exc)
        return

    print("Starting KM2 Image Studio…")
    _launch()


if __name__ == "__main__":
    main()
