# Comparator Folder

Compare two folders to verify:
- files with the same relative names
- files missing from one side
- files with content differences

## Run

1. Open `comparator folder`
2. Double-click `start.bat`
3. The app opens in your browser

## How To Use

1. Load Folder A and Folder B:
   - Use **Select Folder A/B** (recommended on Edge/Chrome)
   - Or use **Fallback input A/B** for browsers without folder picker API
2. Click **Compare Now**
3. Review:
   - **Only in Folder A**
   - **Only in Folder B**
   - **Changed files**
   - **Identical files**
4. Click a changed file to see line-by-line diff

## Notes

- Comparison uses relative file paths from each selected root folder.
- Text diff is shown for readable text files.
- Binary files are detected and reported as binary changed.
- Large text files may use a simplified diff for performance.
