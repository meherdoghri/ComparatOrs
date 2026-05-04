# Process Comparator AI App

This app opens in your browser and checks if list items are present in one or many screenshots.

## Run

1. Double-click `start.bat`
2. The app opens in your default browser.

## How to use

1. Paste screenshots directly with Ctrl+V (you can paste many screenshots one after another).
2. Check that previews are displayed in the screenshot area.
3. Add list items (one line per item).
4. Click **Run Check**.
5. See Found/Missing results.

## Notes

- OCR is done in-browser using Tesseract.js.
- Internet is required the first time to download OCR model files.
- Better image quality gives better matching results.
- You can adjust fuzzy threshold between 0.60 and 1.00.
- The inputs are displayed side by side: screenshot paste area on one side and list area on the other side.
