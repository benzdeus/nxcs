# Font Packaging

This project bundles a Thai-capable font so screenshot output is consistent across environments.

- Bundled font path: `fonts/NotoSansThai-Variable.ttf`
- License file: `fonts/OFL.txt` (SIL Open Font License)
- `code.py` loads this bundled font first, then falls back to system fonts.

If Thai text still appears as boxes, check that `fonts/NotoSansThai-Variable.ttf` exists in your deployed copy of the repository.
