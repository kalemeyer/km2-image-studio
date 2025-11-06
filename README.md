# KM2 Image Studio

Drag & drop product-photo pipeline with background removal, KM2 watermark, color tags/alt text, and auto Finished folder.

## Run it without any jargon

1. **Install Python 3.10 or newer**
   * Windows / macOS: download it from [python.org](https://www.python.org/downloads/) and make sure the "Add python to PATH" checkbox is ticked during the installer.
   * Linux: use your package manager (for example `sudo apt install python3 python3-pip`).

2. **Download this project**
   * Click the green **Code** button on GitHub and choose **Download ZIP**.
   * Once it finishes downloading, unzip it anywhere you like (your Desktop is fine).
   * The folder you just unzipped is the "project folder" people often mention. You do not need to know any special paths—just open that folder in the steps below.

3. **Double-click `KM2_Image_Studio.pyw`**
   * This file hides the console window on Windows/macOS and simply launches the app.
   * The first run may take a moment: it calls `start_km2studio.py` under the hood, which installs Pillow and tkinterdnd2 automatically if they are missing. Background removal (`rembg`) is optional—you will get a reminder explaining how to add it later if you want the transparent PNG feature.
   * On Linux, some desktop environments do not run `.pyw` files directly. In that case, right-click → **Open With Python** or run `python start_km2studio.py` from a terminal in the folder.
   * Prefer the original launcher? You can still double-click `start_km2studio.py` (or run `python start_km2studio.py`) and everything works exactly the same.

4. **Next time you want to open it**, just double-click `KM2_Image_Studio.pyw` again. No extra setup is needed unless you download a fresh copy of the project.

### Get around with the menu bar

The top of the window now includes familiar menus:

- **File → Exit** closes the application.
- **Help → View Help** shows the workflow tips that used to live on the Help button.
- **Help → Check for Updates…** looks online to see whether a newer version is available and walks you through installing it.

### Update without leaving the app

Use **Help → Check for Updates…** (or click the **Update App** button in the lower-left corner) and KM2 Image Studio will:

1. Try `git pull` if it detects that your copy came from `git clone`.
2. Otherwise download the latest ZIP from GitHub, replace the files in place, and prompt you to restart the app.

After the update finishes, close and reopen the program to load the new code. Patch notes for each release are saved locally in the `patch_notes/` folder (for example `patch_notes/v1.3.0.md`), and the latest summary is always mirrored in `PATCH_NOTES.md`.

### Update to the newest version later on (manual options)

If you already have the folder on your computer and just want the latest changes from GitHub, pick whichever option feels easier:

* **Fastest for beginners:** delete your old `km2-image-studio` folder and repeat step 2 above to download the ZIP again. Once unzipped, use the new folder the same way as before.
* **If you use Git:** open a terminal in the project folder and run `git pull`. That command grabs only the files that changed.

After you refresh the files (either method), double-click `start_km2studio.py` again. Python will reuse the packages it already installed unless something new was added, so the update process stays quick.

### Prefer the manual commands?

If you like seeing each step yourself, you can still use the original process:

1. Open a terminal inside the project folder (see hints above).
2. Install the requirements once:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the app manually:
   ```bash
   python km2_launcher.py
   ```

### Optional: install the `km2studio` command

If you like typing shorter commands, you can also install the project in "editable" mode:

```bash
pip install -e .
km2studio
```

The launcher automatically falls back to `km2_launcher.py` when the module cannot be imported, so the command above and the direct `python` call launch the exact same interface.

### Troubleshooting the quick launcher

- If the window does not open and the console shows `Could not install dependencies automatically`, run the command it prints (`python -m pip install -r requirements.txt`) and try `start_km2studio.py` again.
- On Windows, you might need to right-click the file, choose **Open with**, and pick **Python** the first time.
- You can always fall back to the manual commands in the section above; they launch the exact same interface.

### Upload your copy to GitHub

If you want to share your changes online, you can push the folder you downloaded to your own GitHub repository:

1. **Create an empty repository on GitHub.**  
   Go to [github.com/new](https://github.com/new), choose a name, and keep it public or private as you prefer. Do not add a README or `.gitignore`; the folder already contains those.
2. **Initialize git inside your project folder.**  
   Open the terminal that is already inside the folder (from step 3 above) and run:
   ```bash
   git init
   git add .
   git commit -m "Initial import"
   ```
3. **Connect the local folder to the GitHub repository.**  
   Copy the HTTPS URL that GitHub shows (it ends with `.git`) and run:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   ```
   Replace the URL with the one GitHub gave you.
4. **Upload ("push") the files.**  
   ```bash
   git push -u origin main
   ```
   If GitHub suggests using `master` instead of `main`, follow the message it prints. After this command finishes, refresh the repository page and you will see all of your files online.
