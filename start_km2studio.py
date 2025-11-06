"""One-click launcher for KM2 Image Studio with dependency bootstrapping."""
from __future__ import annotations

import json
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import Iterable

REQUIRED_IMPORTS = {
    "PIL": "pillow",
    "tkinterdnd2": "tkinterdnd2",
}

OPTIONAL_IMPORTS = {
    "rembg": "rembg",
}

NOTICE_FILE = Path.home() / ".km2studio" / "optional_packages.json"


def _missing_packages() -> list[str]:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_IMPORTS.items():
        try:
            import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package_name)
    return missing


def _missing_optional() -> list[str]:
    missing: list[str] = []
    for module_name, package_name in OPTIONAL_IMPORTS.items():
        try:
            import_module(module_name)
        except ModuleNotFoundError:
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
        optional_missing = _missing_optional()
        if optional_missing:
            _notify_optional(optional_missing)
    except subprocess.CalledProcessError as exc:
        _notify_install_failure(exc)
        return

    print("Starting KM2 Image Studio…")
    _launch()


def _notify_optional(packages: list[str]) -> None:
    if not packages:
        return

    already_notified = _load_optional_notice()
    new_packages = [pkg for pkg in packages if pkg not in already_notified]
    if not new_packages:
        return

    message = (
        "Optional features like background removal need extra packages.\n"
        + "Missing: "
        + ", ".join(new_packages)
        + "\nInstall later with: python -m pip install "
        + " ".join(new_packages)
    )
    _safe_messagebox("KM2 Image Studio", message)
    _save_optional_notice(already_notified.union(new_packages))


def _notify_install_failure(exc: Exception) -> None:
    message = (
        "Could not install required packages automatically.\n"
        "Run: python -m pip install -r requirements.txt\n\n"
        f"Error: {exc}"
    )
    print("\n⚠️ Could not install dependencies automatically.")
    print("   Please run: python -m pip install -r requirements.txt")
    print("   Error:", exc)
    _safe_messagebox("KM2 Image Studio", message)


def _safe_messagebox(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        return

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def _load_optional_notice() -> set[str]:
    try:
        data = json.loads(NOTICE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(item) for item in data)
    except Exception:
        pass
    return set()


def _save_optional_notice(packages: Iterable[str]) -> None:
    try:
        NOTICE_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTICE_FILE.write_text(json.dumps(sorted(set(packages))), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    main()
