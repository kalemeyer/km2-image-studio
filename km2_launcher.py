"""Fallback launcher for KM2 Image Studio with dependency bootstrapping."""

from __future__ import annotations

import runpy
import subprocess
import sys
from importlib import import_module
from pathlib import Path

REQUIRED_IMPORTS = {
    "PIL": "pillow",
    "rembg": "rembg",
    "tkinterdnd2": "tkinterdnd2",
}


def _ensure_dependencies() -> None:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_IMPORTS.items():
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package_name)

    if not missing:
        return

    cmd = [sys.executable, "-m", "pip", "install", *missing]
    print("Installing missing packages:", " ".join(missing))
    subprocess.check_call(cmd)


def main() -> None:
    """Launch the Tkinter app, even if the module cannot be imported."""

    try:
        _ensure_dependencies()
    except subprocess.CalledProcessError as exc:
        print("\n⚠️ Could not install dependencies automatically.")
        print("   Please run: python -m pip install -r requirements.txt")
        print("   Error:", exc)
        return

    try:
        runpy.run_module("image_studio_app_v3", run_name="__main__")
        return
    except ModuleNotFoundError as err:
        if getattr(err, "name", None) != "image_studio_app_v3":
            raise

    script_path = Path(__file__).with_name("image_studio_app_v3.py")
    if not script_path.exists():
        raise FileNotFoundError(
            "Could not locate image_studio_app_v3.py next to km2_launcher.py"
        )
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
