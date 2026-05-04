# Program Comparator

## Purpose
Program Comparator compares versioned COBOL program files side-by-side and highlights real differences while reducing false positives.

It is designed for folders that contain one base file and multiple variants (for example: `SAV_...`, dated suffixes, install-kit variants).

## What It Does
- Groups files by base name (removes known variant suffixes/prefixes).
- Chooses a current version (left) and an old/variant version (right).
- Applies comparison filters:
  - Ignore full line-number-only lines (optional)
  - Strip leading 6-digit COBOL line numbers (optional)
  - Ignore trailing spaces (optional)
- Computes a Myers-style diff to align insertions/deletions correctly.
- Shows:
  - Diff blocks count
  - Added/removed line totals
  - Next/previous diff navigation
  - File and variant navigation

## Folder Resolution
The comparator can resolve program folders automatically in this order:
1. `Program/prg_S7`
2. `Program/pgm_S7`
3. `Program/prg`
4. `Program/pgm`
5. `Program/prg_S7_copie`
6. `Program/pgm_4YOU`

You can also force a specific folder with environment variable `PGM_DIR`.

## Run
From this folder:
- `start.bat`

Or manually:
- `python server.py`
- Open `http://localhost:8090`

## User Quick Guide
1. Open the program folder.
2. Select a file group from the left panel.
3. Keep these filters enabled for COBOL comparisons:
   - Strip leading numbers
   - Ignore trailing spaces
4. Use diff navigation buttons to jump block by block.

## Notes on Result Interpretation
- “Diff blocks” are logical change regions (closest to Notepad++ understanding of changes).
- `+N` and `-N` show inserted/deleted lines totals, which can be larger than the block count.

## For Copilot / Maintainers: Save Current Code Safely
When preserving the current stable behavior, follow this order:

1. Verify before save:
   - Compare known pair (example: `SAV_250921_XXXXXB0F` vs `XXXXXB0F`) with:
     - Strip leading numbers = ON
     - Ignore trailing spaces = ON
   - Expected: block-level changes close to Notepad++ output.

2. Check modified files:
   - `git status`

3. Commit current working version:
   - `git add "Program comparator/index.html" "Program comparator/server.py" "Program comparator/README.md"`
   - `git commit -m "Program Comparator: stable diff alignment and folder auto-detection"`

4. Optional tag for restore point:
   - `git tag program-comparator-stable-2026-04-23`

5. If working with Copilot on new changes, request:
   - Keep `computeEditScript` backtracking behavior unchanged unless tests prove improvement.
   - Do not remove COBOL filters (leading numbers/trailing spaces) from default workflow.
   - Validate against one known baseline pair before finalizing edits.

### Reusable Prompt for Copilot
Use this when you want Copilot to protect the current stable version:

"Before making changes, preserve Program Comparator stable behavior. Keep Myers diff alignment logic and COBOL filters intact. Validate with SAV_250921_XXXXXB0F vs XXXXXB0F using strip leading numbers + ignore trailing spaces. After changes, run a quick check and summarize whether diff block count still matches expected Notepad++-like result. Then stage and commit only comparator files."

## Troubleshooting
- If no files appear:
  - Confirm folder contains files directly (not only subfolders).
  - Set `PGM_DIR` explicitly.
- If differences look too large:
  - Hard-refresh browser (Ctrl+F5)
  - Re-check filter states
  - Verify selected variants (left/right)
