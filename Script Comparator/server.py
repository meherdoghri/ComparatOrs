#!/usr/bin/env python3
"""
Script Comparator – compares script files in Script/S7 or Script/shl_S7 and Script/4YOU or Script/shl_4YOU.
Run:  python server.py
Then open http://localhost:8091 in your browser.
No external dependencies – uses only Python 3 stdlib.
"""

import http.server
import json
import os
import re
import difflib
import webbrowser
import urllib.parse
from pathlib import Path

PORT = 8091

# ---------------------------------------------------------------------------
# Paths to script folders (relative to this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
SCRIPT_ROOT = SCRIPT_DIR.parent / "Script"


def _resolve_script_dir(env_var: str, candidates: list[str]) -> Path:
  """Resolve a script directory from env var or candidate names."""
  explicit = os.environ.get(env_var)
  if explicit:
    p = Path(explicit)
    if p.exists() and p.is_dir():
      return p

  for name in candidates:
    p = SCRIPT_ROOT / name
    if p.exists() and p.is_dir():
      return p

  return SCRIPT_ROOT / candidates[0]


SCRIPT_S7_DIR = _resolve_script_dir("SCRIPT_S7_DIR", ["S7", "shl_S7"])
SCRIPT_4YOU_DIR = _resolve_script_dir("SCRIPT_4YOU_DIR", ["4YOU", "shl_4YOU"])


# ---------------------------------------------------------------------------
# Suffix patterns that mark a file as a versioned copy of a base script
# ---------------------------------------------------------------------------
SUFFIX_PATTERNS = [
    r"_AV_INSTALL_KIT_\d+",
    r"-\d{6,}[A-Z0-9]*",        # -20191104, -260623
    r"\.\d{6,}",                # .081023
    r"[_.]sv\d{6,}",            # _sv25092013
    r"[_.]svg\d+",              # _svg29122010
    r"\.old$",
    r"\.OLD$",
    r"\.V\d+$",
    r"-OLD$",
    r"-NEW$",
    r"-SV$",
    r"_SAV$",
    r"_ORA$",
    r"-20\d{6,}",               # date-based
]

COMBINED_SUFFIX = re.compile(
    "(" + "|".join(SUFFIX_PATTERNS) + ")+$",
    re.IGNORECASE,
)


def base_name(filename: str) -> str:
    """Strip version suffixes to get the canonical base name."""
    return COMBINED_SUFFIX.sub("", filename)


def get_files_in_dir(script_dir: Path) -> dict:
    """Return dict base_name -> list of (filename, variant) tuples."""
    files = {}
    if not script_dir.exists():
        return files
    for entry in sorted(script_dir.iterdir()):
        if entry.is_file():
            b = base_name(entry.name)
            if b not in files:
                files[b] = []
            files[b].append(entry.name)
    return files


def get_comparison_groups() -> dict:
    """Return files grouped by base name, from both S7 and 4YOU."""
    s7_files = get_files_in_dir(SCRIPT_S7_DIR)
    you_files = get_files_in_dir(SCRIPT_4YOU_DIR)
    
    all_bases = set(s7_files.keys()) | set(you_files.keys())
    groups = {}
    
    for base in sorted(all_bases):
        s7_list = s7_files.get(base, [])
        you_list = you_files.get(base, [])
        groups[base] = {
            "s7": sorted(s7_list),
            "4you": sorted(you_list),
            "has_both": len(s7_list) > 0 and len(you_list) > 0,
            "only_s7": len(s7_list) > 0 and len(you_list) == 0,
            "only_4you": len(s7_list) == 0 and len(you_list) > 0,
        }
    
    return groups


def read_file_lines(script_dir: Path, filename: str) -> list:
    """Read file with fallback encodings."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return (script_dir / filename).read_text(encoding=enc).splitlines(keepends=True)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return []


def compute_diff(lines_a: list, lines_b: list, name_a: str, name_b: str) -> dict:
    """Return a dict with diff blocks and statistics."""
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    blocks = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        blocks.append({
            "tag": tag,
            "a": [l.rstrip("\n").rstrip("\r") for l in lines_a[i1:i2]],
            "b": [l.rstrip("\n").rstrip("\r") for l in lines_b[j1:j2]],
            "a_start": i1 + 1,
            "b_start": j1 + 1,
        })
    
    stats = {
        "total_a": len(lines_a),
        "total_b": len(lines_b),
        "added":   sum(len(b["b"]) for b in blocks if b["tag"] == "insert"),
        "removed": sum(len(b["a"]) for b in blocks if b["tag"] == "delete"),
        "changed": sum(max(len(b["a"]), len(b["b"])) for b in blocks if b["tag"] == "replace"),
        "equal":   sum(len(b["a"]) for b in blocks if b["tag"] == "equal"),
    }
    
    return {
        "blocks": blocks,
        "stats": stats,
        "name_a": name_a,
        "name_b": name_b,
    }


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for API and static files."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
            return
        
        if self.path == "/api/groups":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            groups = get_comparison_groups()
            response = {
                "groups": groups,
                "s7_dir": str(SCRIPT_S7_DIR),
                "you_dir": str(SCRIPT_4YOU_DIR),
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return
        
        if self.path.startswith("/api/compare/"):
            parts = self.path.split("/")
            if len(parts) >= 6:
                base = urllib.parse.unquote(parts[3])
                file_a = urllib.parse.unquote(parts[4])
                file_b = urllib.parse.unquote(parts[5])
                
                lines_a = read_file_lines(SCRIPT_S7_DIR, file_a)
                lines_b = read_file_lines(SCRIPT_4YOU_DIR, file_b)
                
                diff = compute_diff(lines_a, lines_b, file_a, file_b)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(diff).encode("utf-8"))
                return
        
        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress logging."""
        pass


def start_server():
    """Start the HTTP server."""
    server = http.server.HTTPServer(("localhost", PORT), RequestHandler)
    print(f"Script Comparator running at http://localhost:{PORT}")
    print(f"S7 folder: {SCRIPT_S7_DIR}")
    print(f"4YOU folder: {SCRIPT_4YOU_DIR}")
    webbrowser.open(f"http://localhost:{PORT}")
    server.serve_forever()


# ---------------------------------------------------------------------------
# HTML Frontend
# ---------------------------------------------------------------------------
HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Script Comparator</title>
<style>
:root {
  --bg: #0f172a;
  --panel: #111827;
  --panel2: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --accent2: #818cf8;
  --add-bg: #052e16;
  --add-fg: #4ade80;
  --add-border: #166534;
  --del-bg: #450a0a;
  --del-fg: #f87171;
  --del-border: #991b1b;
  --chg-bg: #431407;
  --chg-fg: #fb923c;
  --chg-border: #9a3412;
  --eq-bg: #0f172a;
  --eq-fg: #94a3b8;
  --tag-bg: #1e3a5f;
  --tag-text: #7dd3fc;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: Segoe UI, Roboto, sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── TOP BAR ── */
.topbar {
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  z-index: 20;
  position: sticky;
  top: 0;
}

.topbar h1 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
}

.topbar select,
.topbar button {
  background: var(--panel2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 0.85rem;
  cursor: pointer;
}

.topbar select:focus,
.topbar button:hover {
  outline: none;
  border-color: var(--accent);
}

.topbar button {
  background: #1e40af;
  border-color: #3b82f6;
  color: #fff;
  font-weight: 600;
}

.topbar button:hover {
  background: #2563eb;
}

.badge {
  background: var(--tag-bg);
  color: var(--tag-text);
  border-radius: 99px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 600;
}

.sep {
  flex: 1;
}

/* ── LAYOUT ── */
.layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── SIDEBAR ── */
.sidebar {
  width: 300px;
  min-width: 250px;
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-head {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 600;
}

.sidebar-search {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
}

.sidebar-search input {
  width: 100%;
  background: var(--panel2);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text);
  padding: 6px 8px;
  font-size: 0.8rem;
}

.group-list {
  overflow-y: auto;
  flex: 1;
}

.group-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  transition: background 0.15s;
}

.group-item:hover {
  background: var(--panel2);
}

.group-item.active {
  background: #1e3a5f;
  color: var(--accent);
  font-weight: 600;
}

.group-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-both {
  background: #10b981;
}

.dot-s7-only {
  background: #f59e0b;
}

.dot-4you-only {
  background: #8b5cf6;
}

.group-item .details {
  margin-left: auto;
  font-size: 0.7rem;
  color: var(--muted);
}

/* ── MAIN CONTENT ── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── STATS BAR ── */
.statsbar {
  background: var(--panel2);
  border-bottom: 1px solid var(--border);
  padding: 8px 16px;
  display: flex;
  gap: 20px;
  font-size: 0.8rem;
  align-items: center;
  flex-wrap: wrap;
}

.stat-add {
  color: var(--add-fg);
}

.stat-del {
  color: var(--del-fg);
}

.stat-chg {
  color: var(--chg-fg);
}

.stat-eq {
  color: var(--muted);
}

/* ── DIFF VIEW ── */
.diff-wrap {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 0.78rem;
  table-layout: fixed;
}

.diff-table th {
  background: var(--panel);
  color: var(--muted);
  font-weight: 600;
  padding: 6px 8px;
  border-bottom: 2px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 5;
  text-align: left;
}

.diff-table td {
  padding: 2px 8px;
  vertical-align: top;
  white-space: pre-wrap;
  word-break: break-word;
  border-bottom: 1px solid #1e293b;
}

.ln {
  width: 50px;
  color: var(--muted);
  text-align: right;
  user-select: none;
  font-size: 0.7rem;
  padding-right: 10px;
  border-right: 1px solid var(--border);
}

.col-a {
  width: 50%;
}

.col-b {
  width: 50%;
}

.eq td.code {
  background: var(--eq-bg);
  color: var(--eq-fg);
}

.add td.code {
  background: var(--add-bg);
  color: var(--add-fg);
  border-left: 3px solid var(--add-border);
}

.del td.code {
  background: var(--del-bg);
  color: var(--del-fg);
  border-left: 3px solid var(--del-border);
}

.chg td.code {
  background: var(--chg-bg);
  color: var(--chg-fg);
  border-left: 3px solid var(--chg-border);
}

.empty td.code {
  background: var(--panel);
  color: transparent;
}

/* collapsed equal blocks */
.fold-row td {
  background: var(--panel);
  color: var(--muted);
  text-align: center;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 4px;
}

.fold-row:hover td {
  background: var(--panel2);
  color: var(--accent);
}

/* ── EMPTY STATE ── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  gap: 12px;
}

.empty-state svg {
  opacity: 0.3;
  width: 80px;
  height: 80px;
}

.empty-state p {
  font-size: 0.9rem;
  text-align: center;
  max-width: 400px;
}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <h1>📜 Script Comparator</h1>
  <div class="sep"></div>
  <span id="status" style="font-size: 0.8rem; color: var(--muted);">Loading...</span>
</div>

<div class="layout">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-head">
      Scripts <span id="group-count" class="badge">0</span>
    </div>
    <div class="sidebar-search">
      <input id="search" placeholder="Filter scripts…" />
    </div>
    <div class="group-list" id="group-list"></div>
  </div>

  <!-- MAIN -->
  <div class="main" id="main">
    <div class="empty-state" id="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <path d="M3 6l2-2h14l2 2v12l-2 2H5l-2-2V6z"/>
        <path d="M8 10h8"/>
        <path d="M8 14h8"/>
        <path d="M8 18h4"/>
      </svg>
      <p>Select a script above to compare<br/>S7 and 4YOU versions</p>
    </div>
    <div id="statsbar" class="statsbar" style="display: none;"></div>
    <div class="diff-wrap" id="diff-wrap" style="display: none;">
      <table class="diff-table" id="diff-table">
        <thead>
          <tr>
            <th class="ln">#</th>
            <th class="col-a" id="th-a">S7 File</th>
            <th class="ln">#</th>
            <th class="col-b" id="th-b">4YOU File</th>
          </tr>
        </thead>
        <tbody id="diff-body"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const FOLD_THRESHOLD = 5;
let allGroups = {};
let currentGroup = null;

async function init() {
  try {
    const res = await fetch('/api/groups');
    const data = await res.json();
    allGroups = data.groups;
    renderGroupList(allGroups);
    updateStatus(`${Object.keys(allGroups).length} scripts found`);
  } catch (err) {
    updateStatus('Error loading scripts');
    console.error(err);
  }
}

function updateStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function renderGroupList(groups) {
  const list = document.getElementById('group-list');
  const keys = Object.keys(groups).sort();
  document.getElementById('group-count').textContent = keys.length;
  list.innerHTML = '';
  
  keys.forEach(base => {
    const group = groups[base];
    const div = document.createElement('div');
    div.className = 'group-item' + (base === currentGroup ? ' active' : '');
    div.dataset.base = base;
    
    let dotClass = 'dot-s7-only';
    if (group.has_both) {
      dotClass = 'dot-both';
    } else if (group.only_4you) {
      dotClass = 'dot-4you-only';
    }
    
    const s7Count = group.s7.length;
    const youCount = group['4you'].length;
    
    let detailsText = '';
    if (group.has_both) {
      detailsText = `${s7Count} / ${youCount}`;
    } else if (group.only_s7) {
      detailsText = `${s7Count} / —`;
    } else {
      detailsText = `— / ${youCount}`;
    }
    
    div.innerHTML = 
      `<span class="dot ${dotClass}"></span>` +
      `<span>${base}</span>` +
      `<span class="details">${detailsText}</span>`;
    
    div.onclick = () => selectGroup(base, groups);
    list.appendChild(div);
  });
}

function filterGroups() {
  const search = document.getElementById('search').value.toLowerCase();
  const items = document.querySelectorAll('.group-item');
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    item.style.display = text.includes(search) ? '' : 'none';
  });
}

function selectGroup(base, groups) {
  currentGroup = base;
  document.querySelectorAll('.group-item').forEach(el => {
    el.classList.remove('active');
  });
  document.querySelector(`[data-base="${base}"]`).classList.add('active');
  
  const group = groups[base];
  const s7Files = group.s7;
  const youFiles = group['4you'];
  
  if (group.has_both && s7Files.length > 0 && youFiles.length > 0) {
    // Compare first versions of each
    compareFiles(base, s7Files[0], youFiles[0]);
  } else {
    showEmpty(`This script exists only in ${group.only_s7 ? 'S7' : '4YOU'}`);
  }
}

async function compareFiles(base, fileA, fileB) {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('diff-wrap').style.display = 'flex';
  document.getElementById('statsbar').style.display = 'flex';
  
  try {
    const res = await fetch(`/api/compare/${encodeURIComponent(base)}/${encodeURIComponent(fileA)}/${encodeURIComponent(fileB)}`);
    const diff = await res.json();
    
    document.getElementById('th-a').textContent = `S7: ${diff.name_a}`;
    document.getElementById('th-b').textContent = `4YOU: ${diff.name_b}`;
    
    renderDiff(diff);
    updateStats(diff.stats);
  } catch (err) {
    console.error(err);
    updateStatus('Error comparing files');
  }
}

function renderDiff(diff) {
  const tbody = document.getElementById('diff-body');
  tbody.innerHTML = '';
  
  const blocks = diff.blocks;
  
  blocks.forEach((block, blockIdx) => {
    if (block.tag === 'equal' && block.a.length > FOLD_THRESHOLD) {
      // Fold equal block
      const tr = document.createElement('tr');
      tr.className = 'fold-row';
      tr.innerHTML = `<td class="ln"></td><td colspan="3" style="text-align:center;">↓ ${block.a.length} equal lines ↓</td>`;
      tbody.appendChild(tr);
      return;
    }
    
    const maxLen = Math.max(block.a.length, block.b.length);
    for (let i = 0; i < maxLen; i++) {
      const tr = document.createElement('tr');
      const lineA = block.a[i] || '';
      const lineB = block.b[i] || '';
      const lineNumA = block.a_start + i;
      const lineNumB = block.b_start + i;
      
      let rowClass = block.tag === 'equal' ? 'eq' : block.tag === 'insert' ? 'add' : block.tag === 'delete' ? 'del' : 'chg';
      if (!lineA || !lineB) rowClass = block.tag === 'insert' ? 'add' : 'del';
      
      tr.className = rowClass;
      tr.innerHTML = `
        <td class="ln">${lineA ? lineNumA : ''}</td>
        <td class="code col-a">${escapeHtml(lineA)}</td>
        <td class="ln">${lineB ? lineNumB : ''}</td>
        <td class="code col-b">${escapeHtml(lineB)}</td>
      `;
      tbody.appendChild(tr);
    }
  });
}

function updateStats(stats) {
  const statsbar = document.getElementById('statsbar');
  statsbar.innerHTML = `
    <span class="stat-eq">📊 ${stats.equal} equal lines</span>
    <span class="stat-add">➕ ${stats.added} added</span>
    <span class="stat-del">➖ ${stats.removed} removed</span>
    <span class="stat-chg">✏️ ${stats.changed} modified</span>
  `;
}

function showEmpty(msg) {
  document.getElementById('empty-state').style.display = 'flex';
  document.getElementById('diff-wrap').style.display = 'none';
  document.getElementById('statsbar').style.display = 'none';
  document.getElementById('empty-state').querySelector('p').textContent = msg;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

document.getElementById('search').addEventListener('input', filterGroups);
init();
</script>

</body>
</html>
"""

if __name__ == "__main__":
    start_server()
