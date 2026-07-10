# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small Python/Tkinter tool that batch-masks (blacks out) fixed regions of same-layout PDFs — e.g. payroll/HR documents where the same fields (employee ID, address, birthdate, ...) sit at the same coordinates across every file. Distributed to non-technical end users as double-clickable `PDFMaskingTool`/`MaskPicker` apps (PyInstaller), not as a Python package.

## Commands

Install dependencies:
```
pip install -r requirements.txt
```

Run directly (dev):
```
python main.py          # masks input/*.pdf -> output/*_masked.pdf using mask_coords.json
python mask_picker.py   # GUI to draw mask rectangles on input/*.pdf, saves mask_coords.json
python calibrate.py     # headless fallback: writes coordinate-grid PNGs to calibration/
```

Build the double-clickable apps locally (only produces a binary for the OS you run it on — PyInstaller cannot cross-compile):
```
pip install pyinstaller
python3 -m PyInstaller --windowed --name PDFMaskingTool main.py   # macOS: dist/PDFMaskingTool.app
python3 -m PyInstaller --windowed --name MaskPicker mask_picker.py

# Windows uses --onefile --noconsole instead of --windowed (see .github/workflows/build-exe.yml)
```

Windows builds happen in CI (this Mac can't produce a `.exe`): pushing changes to `main.py`, `mask_picker.py`, `requirements.txt`, or the workflow file itself triggers `.github/workflows/build-exe.yml` on `windows-latest`, which builds both exes and uploads them as a single `PDFMaskingTool-windows-exe` artifact. Check/watch a run and grab the artifact with:
```
gh run list -R daichitsuchiya39-creator/pdf-masking-tool -L 3
gh run watch <run-id> -R daichitsuchiya39-creator/pdf-masking-tool --exit-status
gh run download <run-id> -R daichitsuchiya39-creator/pdf-masking-tool
```

No test suite or linter is configured.

## Architecture

**Three scripts share one coordinate system and one on-disk contract**, but are otherwise independent entry points (each is packaged as its own app):

- `main.py` — the masking engine. Rasterizes each PDF page via `page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))` (`ZOOM=2`), draws black rectangles over it with `PIL.ImageDraw`, then re-inserts the flattened image as a new PDF page (this is why output PDFs are image-only, not searchable text). Mask rectangles are always in **PDF points (pt)**, origin top-left, matching `page.rect` — they get multiplied by `ZOOM` only at draw time (`main.py`'s `scaled_rect`). Getting that scaling wrong was a real past bug: it makes masks land at half their intended offset.
- `mask_picker.py` — interactive calibration GUI. Lets a user drag rectangles on rendered PDF pages and saves them to `mask_coords.json`, keyed by `{file_stem: {page_no: [{"label", "rect"}]}}`. It also imports `MASKS` from `main.py` (best-effort, wrapped in `try/except`) purely to overlay the *currently active* mask as a blue dashed reference while editing.
- `calibrate.py` — non-interactive fallback for environments without a usable GUI: overlays a labeled pt-coordinate grid on each page image so coordinates can be read off by eye and `mask_coords.json` edited by hand.

**`mask_coords.json` is the single source of truth for what gets masked**, read fresh on every `main.py` run via `load_masks()`. Because the tool's whole premise is "one layout, batch-applied to every file in `input/`", `load_masks()` deliberately ignores the per-file-stem keying and just takes `list(raw.values())[-1]` — the most recently *added* top-level entry — and applies it to *all* PDFs in `input/`. If the file is missing/empty/corrupt, it falls back to the hardcoded `DEFAULT_MASKS` dict in `main.py`. Mixing genuinely different-layout PDFs in one `input/` run will silently mis-mask them; that's a design tradeoff of the tool, not a bug to fix casually.

**Packaged-app gotchas (already fixed once — preserve these patterns if touching startup code in `main.py`/`mask_picker.py`):**
1. PyInstaller `--windowed`/`--noconsole` builds set `sys.stdout`/`sys.stderr` to `None`. Any `print()` or library warning write then raises `AttributeError` before any UI ever shows, and the process exits silently with no crash report. Both entry scripts guard this at the top by redirecting to `os.devnull` when `None`.
2. Double-clicking an exe/`.app` does **not** set the working directory to the executable's folder — macOS `.app` launches especially can land on `/`. Both scripts resolve `input/`, `output/`, and `mask_coords.json` relative to `BASE_DIR`, computed from `sys.executable` when frozen (walking up 3 parents out of `.app/Contents/MacOS/` on macOS) rather than from `cwd`.
3. Both scripts wrap their entire `__main__` block (including `tk.Tk()` itself) in `try/except`, writing any unhandled traceback to `debug.log` next to the executable — the only way to debug a `--noconsole` build in the field.

macOS apps are ad-hoc signed by PyInstaller (not notarized), so first launch triggers Gatekeeper; Windows exes are unsigned, so first launch triggers SmartScreen. Both are expected and documented in `README.md`, not bugs.

See `README.md` for the end-user manual and a dated work log of what's been fixed/verified so far (macOS confirmed working; Windows exe builds green in CI but not yet run on real Windows hardware).
