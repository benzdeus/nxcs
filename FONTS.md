# Font Packaging

This project bundles a Thai-capable font so screenshot output is consistent across environments.

- Bundled font paths:
  - `fonts/NotoSansThai-Variable.ttf`
  - `fonts/NotoSansThaiLooped-Variable.ttf`
- License file: `fonts/OFL.txt` (SIL Open Font License)
- `code.py` uses monospaced font for normal terminal columns and Thai font fallback for Thai glyphs.

If Thai text still appears as boxes, check that both bundled Thai fonts exist in your deployed copy of the repository.
