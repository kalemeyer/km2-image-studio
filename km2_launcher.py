import runpy
from pathlib import Path

def main():
    """Launch the Tkinter app, even if the module cannot be imported."""
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
