# Side-by-Side Comparator (2 or 3 files)

Open this file in your browser:

- `tools/three_way_comparator.html`

## How to use

1. Select mode: **2 Files** or **3 Files** using the toggle at the top.
2. Set names (example: `S7 standard`, `S7 Modified`, and optionally `4YOU`).
3. Paste content of each version in its textarea.
4. Click **Compare**.
5. Scroll side by side (scroll is synced).
6. Optional: check **Show only different lines**.
7. In 3-file mode, use **Check Delta In V3** to verify delta presence.
8. Use **Clear** to start a new comparison.

## Notes

- This is a manual visual comparator (Notepad++ style concept) for **3 files at once**.
- It highlights lines where at least one file differs.
- It does not modify your files.
- It runs in **exact mode by default** (recommended for sensitive files).
- Optional: enable **Ignore trailing spaces** only if you intentionally want to ignore right-side whitespace.
- For very large files, exact alignment can be heavy; if needed, compare by logical sections/blocks for maximum correctness.
