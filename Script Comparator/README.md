# Script Comparator

A lightweight web-based tool to compare shell scripts between **S7** and **4YOU** versions, identify differences, and track changes.

## Features

✨ **Quick & Easy**
- Compare scripts from `Script/S7` + `Script/4YOU` or `Script/shl_S7` + `Script/shl_4YOU`
- Identify common scripts across both versions
- See scripts unique to each version

📊 **Detailed Comparison**
- Line-by-line diff with syntax highlighting
- Automatic line number removal and trailing space handling
- Statistics: added, removed, modified, and equal lines

🔍 **Search & Filter**
- Filter scripts by name
- Identify modified vs unmodified files

## How to Use

### 1. Start the Server

**Option A - Using the batch file (Windows):**
```bash
start.bat
```

**Option B - Direct Python:**
```bash
python server.py
```

If `python` is not available in your shell, use:
```bash
py -3 server.py
```

The server will start on **http://localhost:8091** and automatically open in your browser.

### 2. Navigate the Interface

1. **Sidebar (Left)** - Shows all scripts with their versions:
   - 🟢 Green dot: Script exists in both S7 and 4YOU
   - 🟠 Orange dot: Script only in S7
   - 🟣 Purple dot: Script only in 4YOU
   - Numbers show: `S7 versions / 4YOU versions`

2. **Search** - Filter scripts by name in the search box

3. **Main View (Right)** - Shows detailed diff:
   - **Equal lines** (gray): Identical content
   - **Added lines** (green): Only in 4YOU
   - **Removed lines** (red): Only in S7
   - **Modified lines** (orange): Changed between versions

## File Structure

```
Script Comparator/
├── server.py         # Backend server (Python)
├── start.bat         # Quick launcher (Windows)
├── README.md         # This file
```

## Requirements

- Python 3.6+
- Web browser (Chrome, Firefox, Edge, Safari)
- One of the following folder structures:
  ```
  Script/
  ├── S7/
  │   └── [script files]
  └── 4YOU/
      └── [script files]
  ```
  ```
  Script/
  ├── shl_S7/
  │   └── [script files]
  └── shl_4YOU/
      └── [script files]
  ```

## API Endpoints

The server provides the following REST endpoints:

- `GET /` - HTML interface
- `GET /api/groups` - Get all scripts grouped by base name
- `GET /api/compare/{base}/{fileA}/{fileB}` - Get diff between two files

## How It Works

1. **Script Discovery**: Scans both S7 and 4YOU folders for scripts
2. **Grouping**: Groups scripts by base name (ignoring version suffixes)
3. **Comparison**: Uses Python's `difflib` to compute line-by-line differences
4. **Display**: Renders diff in an interactive table with syntax highlighting

## Example Scenario

If you have:
```
Script/shl_S7/
  ├── deploy.sh
  └── deploy.sh_old

Script/shl_4YOU/
  ├── deploy.sh
  └── utils.sh
```

The comparator will:
1. Show 2 scripts: **deploy** and **utils**
2. For **deploy**: Show green dot (both versions), compare `S7/deploy.sh` with `4YOU/deploy.sh`
3. For **utils**: Show purple dot (4YOU only)

## Troubleshooting

### Server won't start
- Ensure Python 3.6+ is installed: `python --version`
- Check that port 8091 is not in use

### Folders not found
- Verify one of these folder pairs exists:
  - `Script/S7/` and `Script/4YOU/`
  - `Script/shl_S7/` and `Script/shl_4YOU/`

### Encoding issues
- The comparator handles UTF-8, Latin-1, and CP1252 encodings automatically

## Notes

- The comparator automatically strips common version suffixes (e.g., `_old`, `.sv20230101`)
- Large files (>10,000 lines) may take a moment to compare
- All processing is done locally – no data is sent elsewhere
