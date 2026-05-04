#!/usr/bin/env python3
"""
Program Comparator – compares versioned COBOL program files in Program/prg_S7 or Program/pgm_S7.
Run:  python server.py
Then open http://localhost:8090 in your browser.
No external dependencies – uses only Python 3 stdlib.
"""

import http.server
import json
import os
import re
import difflib
import threading
import webbrowser
import urllib.parse
from pathlib import Path

PORT = 8090

# ---------------------------------------------------------------------------
# Path to the program folder (relative to this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent


def resolve_program_dir() -> Path:
  explicit = os.environ.get("PGM_DIR")
  if explicit:
    p = Path(explicit)
    if p.exists() and p.is_dir():
      return p

  candidates = [
    SCRIPT_DIR.parent / "Program" / "prg_S7",
    SCRIPT_DIR.parent / "Program" / "pgm_S7",
    SCRIPT_DIR.parent / "Program" / "prg",
    SCRIPT_DIR.parent / "Program" / "pgm",
    SCRIPT_DIR.parent / "Program" / "prg_S7_copie",
    SCRIPT_DIR.parent / "Program" / "pgm_4YOU",
  ]
  for candidate in candidates:
    if candidate.exists() and candidate.is_dir():
      return candidate

  return SCRIPT_DIR.parent / "Program" / "prg_S7"


PGM_DIR = resolve_program_dir()

# ---------------------------------------------------------------------------
# Suffix patterns that mark a file as a versioned copy of a base program
# Order matters – more specific first
# ---------------------------------------------------------------------------
SUFFIX_PATTERNS = [
    r"-AV_INSTALL_KIT_\d+",
    r"_AV_INSTALL_KIT_\d+",
    r"-\d{6,}[A-Z0-9]*",        # -20191104CMPAS, -010120-AVPJ8, -260623
    r"\.\d{6,}",                 # .081023, .sv31052014
    r"[_.]sv\d{6,}",             # _sv25092013, .sv10022014
    r"[_.]svg\d+",               # _svg29122010
    r"-svg[A-Z0-9-]+",           # -svgAV-CIB2528
    r"-cst\d+",                  # -cst20140327
    r"\.avecDisplays",
    r"\.avecdisplay",
    r"\.DGX",
    r"\.saveWass",
    r"\.svg[-_]\w+",             # .svg_2610
    r"\.old$",
    r"\.OLD$",
    r"\.V\d+$",
    r"-OLD$",
    r"-NEW$",
    r"-SV$",
    r"_SAVSHS",
    r"_SAVTAH",
    r"_SAV$",
    r"_ORA$",
    r"_DRJ$",
    r"_STND$",
    r"_DISPL$",
    r"_CZW$",
    r"_SVE$",
    r"_SBA$",
    r"_svg$",
    r"_DISPL$",
    r"-20\d{6,}",                # date-based
    r"-\d{2}0\d{3,}",
    r"_avant_\w+",               # _avant_CIB-2835
    r"_avec_\w+",                # _avec_GRP-1067
    r"_av-\w+",
    r"-\w{4,}-\w{2,}",          # -AVPJ8 etc  (fallback)
]

COMBINED_SUFFIX = re.compile(
    "(" + "|".join(SUFFIX_PATTERNS) + ")+$",
    re.IGNORECASE,
)


def base_name(filename: str) -> str:
    """Strip version suffixes to get the canonical base name."""
    return COMBINED_SUFFIX.sub("", filename)


def group_files(pgm_dir: Path):
    """Return dict  base_name -> sorted list of filenames."""
    groups: dict[str, list[str]] = {}
    if not pgm_dir.exists():
        return groups
    for entry in sorted(pgm_dir.iterdir()):
        if entry.is_file():
            b = base_name(entry.name)
            groups.setdefault(b, []).append(entry.name)
    # Only keep groups that have more than one member OR a single member
    # (we show everything, the UI will highlight multi-version ones)
    return groups


def read_file_lines(pgm_dir: Path, filename: str) -> list[str]:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return (pgm_dir / filename).read_text(encoding=enc).splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
    return []


def compute_diff(lines_a: list[str], lines_b: list[str], name_a: str, name_b: str):
    """Return a list of diff blocks for the frontend."""
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
    return {"blocks": blocks, "stats": stats, "name_a": name_a, "name_b": name_b}


# ---------------------------------------------------------------------------
# HTML frontend (single-page app bundled inline)
# ---------------------------------------------------------------------------
HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Program Comparator – pgm</title>
<style>
:root{
  --bg:#0f172a; --panel:#111827; --panel2:#1e293b; --border:#334155;
  --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --accent2:#818cf8;
  --add-bg:#052e16; --add-fg:#4ade80; --add-border:#166534;
  --del-bg:#450a0a; --del-fg:#f87171; --del-border:#991b1b;
  --chg-bg:#431407; --chg-fg:#fb923c; --chg-border:#9a3412;
  --eq-bg:#0f172a;  --eq-fg:#94a3b8;
  --tag-bg:#1e3a5f; --tag-text:#7dd3fc;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:Segoe UI,Roboto,sans-serif;height:100vh;display:flex;flex-direction:column}
/* ── TOP BAR ── */
.topbar{background:var(--panel);border-bottom:1px solid var(--border);padding:10px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;z-index:20;position:sticky;top:0}
.topbar h1{font-size:1rem;font-weight:700;color:var(--accent);white-space:nowrap}
.topbar select,.topbar button{background:var(--panel2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:5px 10px;font-size:.85rem;cursor:pointer}
.topbar select:focus,.topbar button:hover{outline:none;border-color:var(--accent)}
.topbar button{background:#1e40af;border-color:#3b82f6;color:#fff;font-weight:600}
.topbar button:hover{background:#2563eb}
.badge{background:var(--tag-bg);color:var(--tag-text);border-radius:99px;padding:2px 8px;font-size:.75rem;font-weight:600}
.sep{flex:1}
/* ── STATS BAR ── */
.statsbar{background:var(--panel2);border-bottom:1px solid var(--border);padding:6px 16px;display:flex;gap:18px;font-size:.8rem;align-items:center}
.stat-add{color:var(--add-fg)} .stat-del{color:var(--del-fg)} .stat-chg{color:var(--chg-fg)} .stat-eq{color:var(--muted)}
/* ── DIFF VIEW ── */
.diff-wrap{flex:1;overflow:auto;display:flex;flex-direction:column}
.diff-table{width:100%;border-collapse:collapse;font-family:'JetBrains Mono','Cascadia Code',Consolas,monospace;font-size:.78rem;table-layout:fixed}
.diff-table th{background:var(--panel);color:var(--muted);font-weight:600;padding:4px 8px;border-bottom:2px solid var(--border);position:sticky;top:0;z-index:5}
.diff-table td{padding:1px 8px;vertical-align:top;white-space:pre-wrap;word-break:break-all;border-bottom:1px solid #1e293b}
.ln{width:44px;color:var(--muted);text-align:right;user-select:none;font-size:.7rem;padding-right:10px;border-right:1px solid var(--border)}
.col-a{width:50%} .col-b{width:50%}
.eq   td.code{background:var(--eq-bg);color:var(--eq-fg)}
.add  td.code{background:var(--add-bg);color:var(--add-fg);border-left:3px solid var(--add-border)}
.del  td.code{background:var(--del-bg);color:var(--del-fg);border-left:3px solid var(--del-border)}
.chg  td.code{background:var(--chg-bg);color:var(--chg-fg);border-left:3px solid var(--chg-border)}
.empty td.code{background:var(--panel);color:transparent}
/* collapsed equal blocks */
.fold-row td{background:var(--panel);color:var(--muted);text-align:center;cursor:pointer;font-size:.75rem;padding:3px}
.fold-row:hover td{background:var(--panel2);color:var(--accent)}
/* ── LEFT PANEL ── */
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:260px;min-width:200px;background:var(--panel);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.sidebar-head{padding:8px 12px;border-bottom:1px solid var(--border);font-size:.8rem;color:var(--muted)}
.sidebar-search{padding:6px 10px;border-bottom:1px solid var(--border)}
.sidebar-search input{width:100%;background:var(--panel2);border:1px solid var(--border);border-radius:5px;color:var(--text);padding:4px 8px;font-size:.8rem}
.group-list{overflow-y:auto;flex:1}
.group-item{padding:6px 12px;cursor:pointer;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:6px;font-size:.8rem}
.group-item:hover{background:var(--panel2)}
.group-item.active{background:#1e3a5f;color:var(--accent)}
.group-item .cnt{margin-left:auto;color:var(--muted);font-size:.7rem}
.group-item .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.dot-multi{background:#f59e0b} .dot-single{background:#334155}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
/* ── EMPTY STATE ── */
.empty-state{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);gap:8px}
.empty-state svg{opacity:.3}
</style>
</head>
<body>
<!-- TOP BAR -->
<div class="topbar">
  <h1>⚡ Program Comparator</h1>
  <span id="pgm-path" style="color:var(--muted);font-size:.78rem"></span>
  <div class="sep"></div>
  <select id="sel-a" style="max-width:200px"><option value="">— version A —</option></select>
  <select id="sel-b" style="max-width:200px"><option value="">— version B —</option></select>
  <button id="btn-compare">Compare ▶</button>
  <span id="diff-badge" class="badge" style="display:none"></span>
</div>

<div class="layout">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-head">
      Programs &nbsp;<span id="group-count" class="badge">0</span>
      &nbsp;<span style="font-size:.7rem">(<span id="multi-count">0</span> with variants)</span>
    </div>
    <div class="sidebar-search">
      <input id="search" placeholder="Filter programs…" oninput="filterGroups()"/>
    </div>
    <div class="group-list" id="group-list"></div>
  </div>

  <!-- MAIN -->
  <div class="main" id="main">
    <div class="empty-state" id="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
        <rect x="3" y="3" width="8" height="18" rx="1"/><rect x="13" y="3" width="8" height="18" rx="1"/>
        <line x1="6" y1="7" x2="9" y2="7"/><line x1="6" y1="10" x2="9" y2="10"/>
        <line x1="16" y1="7" x2="19" y2="7"/><line x1="16" y1="10" x2="19" y2="10"/>
      </svg>
      <p>Select a program on the left,<br>choose versions A &amp; B, then click <b>Compare</b>.</p>
    </div>
    <div id="statsbar" class="statsbar" style="display:none"></div>
    <div class="diff-wrap" id="diff-wrap" style="display:none">
      <table class="diff-table" id="diff-table">
        <thead>
          <tr>
            <th class="ln">#</th>
            <th class="col-a" id="th-a">Version A</th>
            <th class="ln">#</th>
            <th class="col-b" id="th-b">Version B</th>
          </tr>
        </thead>
        <tbody id="diff-body"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const FOLD_THRESHOLD = 5; // collapse equal blocks longer than this
let allGroups = {};
let currentGroup = null;

async function init() {
  const res = await fetch('/api/groups');
  const data = await res.json();
  allGroups = data.groups;
  document.getElementById('pgm-path').textContent = data.pgm_dir;
  renderGroupList(allGroups);
}

function renderGroupList(groups) {
  const list = document.getElementById('group-list');
  const keys = Object.keys(groups).sort();
  const multi = keys.filter(k => groups[k].length > 1);
  document.getElementById('group-count').textContent = keys.length;
  document.getElementById('multi-count').textContent = multi.length;
  list.innerHTML = '';
  keys.forEach(base => {
    const files = groups[base];
    const div = document.createElement('div');
    div.className = 'group-item' + (base === currentGroup ? ' active' : '');
    div.dataset.base = base;
    const isMulti = files.length > 1;
    div.innerHTML =
      `<span class="dot ${isMulti ? 'dot-multi' : 'dot-single'}"></span>` +
      `<span>${base}</span>` +
      `<span class="cnt">${files.length}</span>`;
    div.addEventListener('click', () => selectGroup(base, files));
    list.appendChild(div);
  });
}

function filterGroups() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = {};
  Object.keys(allGroups).forEach(k => {
    if (k.toLowerCase().includes(q)) filtered[k] = allGroups[k];
  });
  renderGroupList(filtered);
}

function selectGroup(base, files) {
  currentGroup = base;
  // update sidebar active state
  document.querySelectorAll('.group-item').forEach(el => {
    el.classList.toggle('active', el.dataset.base === base);
  });
  // populate selects
  const selA = document.getElementById('sel-a');
  const selB = document.getElementById('sel-b');
  selA.innerHTML = '';
  selB.innerHTML = '';
  files.forEach(f => {
    selA.appendChild(new Option(f, f));
    selB.appendChild(new Option(f, f));
  });
  // default: first vs second (if exists)
  if (files.length >= 2) {
    selA.selectedIndex = 0;
    selB.selectedIndex = 1;
  }
  // auto-compare if 2+ files
  if (files.length >= 2) compareFiles();
  else resetDiff();
}

async function compareFiles() {
  const a = document.getElementById('sel-a').value;
  const b = document.getElementById('sel-b').value;
  if (!a || !b || a === b) { resetDiff(); return; }

  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('diff-wrap').style.display = 'none';
  document.getElementById('statsbar').style.display = 'none';
  document.getElementById('diff-body').innerHTML =
    '<tr><td colspan="4" style="padding:20px;text-align:center;color:var(--muted)">Loading…</td></tr>';
  document.getElementById('diff-wrap').style.display = '';

  const res = await fetch(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
  const data = await res.json();
  if (data.error) { alert(data.error); return; }

  renderDiff(data);
}

function resetDiff() {
  document.getElementById('empty-state').style.display = '';
  document.getElementById('diff-wrap').style.display = 'none';
  document.getElementById('statsbar').style.display = 'none';
  document.getElementById('diff-badge').style.display = 'none';
}

function renderDiff(data) {
  const { blocks, stats, name_a, name_b } = data;
  document.getElementById('th-a').textContent = name_a;
  document.getElementById('th-b').textContent = name_b;

  // stats bar
  const hasDiff = stats.added + stats.removed + stats.changed > 0;
  document.getElementById('diff-badge').style.display = '';
  document.getElementById('diff-badge').textContent =
    hasDiff ? '≠ differences found' : '✓ identical';
  document.getElementById('diff-badge').style.background =
    hasDiff ? '#7c2d12' : '#052e16';
  document.getElementById('statsbar').style.display = '';
  document.getElementById('statsbar').innerHTML =
    `<span class="stat-add">+${stats.added} added</span>` +
    `<span class="stat-del">−${stats.removed} removed</span>` +
    `<span class="stat-chg">~ ${stats.changed} changed</span>` +
    `<span class="stat-eq">${stats.equal} equal</span>` +
    `<span style="margin-left:auto;color:var(--muted)">${stats.total_a} lines → ${stats.total_b} lines</span>`;

  const tbody = document.getElementById('diff-body');
  tbody.innerHTML = '';

  blocks.forEach(block => {
    const { tag, a, b, a_start, b_start } = block;

    if (tag === 'equal') {
      if (a.length > FOLD_THRESHOLD * 2) {
        // show first + last FOLD_THRESHOLD lines, fold the rest
        emitRows(tbody, 'eq', a.slice(0, FOLD_THRESHOLD), b.slice(0, FOLD_THRESHOLD), a_start, b_start);
        const foldCount = a.length - FOLD_THRESHOLD * 2;
        const foldRow = document.createElement('tr');
        foldRow.className = 'fold-row';
        foldRow.innerHTML = `<td colspan="4">▸ ${foldCount} equal lines hidden — click to expand</td>`;
        const foldedA = a.slice(FOLD_THRESHOLD, a.length - FOLD_THRESHOLD);
        const foldedB = b.slice(FOLD_THRESHOLD, b.length - FOLD_THRESHOLD);
        const fa = a_start + FOLD_THRESHOLD, fb = b_start + FOLD_THRESHOLD;
        foldRow.addEventListener('click', () => {
          const rows = makeRows('eq', foldedA, foldedB, fa, fb);
          rows.forEach(r => tbody.insertBefore(r, foldRow));
          foldRow.remove();
        });
        tbody.appendChild(foldRow);
        emitRows(tbody, 'eq',
          a.slice(a.length - FOLD_THRESHOLD),
          b.slice(b.length - FOLD_THRESHOLD),
          a_start + a.length - FOLD_THRESHOLD,
          b_start + b.length - FOLD_THRESHOLD);
      } else {
        emitRows(tbody, 'eq', a, b, a_start, b_start);
      }
      return;
    }

    if (tag === 'insert') {
      const maxLen = b.length;
      for (let i = 0; i < maxLen; i++) {
        const tr = document.createElement('tr');
        tr.className = 'add';
        tr.innerHTML =
          `<td class="ln"></td><td class="code empty"></td>` +
          `<td class="ln">${b_start + i}</td><td class="code">${esc(b[i] ?? '')}</td>`;
        tbody.appendChild(tr);
      }
      return;
    }

    if (tag === 'delete') {
      for (let i = 0; i < a.length; i++) {
        const tr = document.createElement('tr');
        tr.className = 'del';
        tr.innerHTML =
          `<td class="ln">${a_start + i}</td><td class="code">${esc(a[i] ?? '')}</td>` +
          `<td class="ln"></td><td class="code empty"></td>`;
        tbody.appendChild(tr);
      }
      return;
    }

    if (tag === 'replace') {
      const maxLen = Math.max(a.length, b.length);
      for (let i = 0; i < maxLen; i++) {
        const tr = document.createElement('tr');
        tr.className = 'chg';
        tr.innerHTML =
          `<td class="ln">${i < a.length ? a_start + i : ''}</td>` +
          `<td class="code">${esc(a[i] ?? '')}</td>` +
          `<td class="ln">${i < b.length ? b_start + i : ''}</td>` +
          `<td class="code">${esc(b[i] ?? '')}</td>`;
        tbody.appendChild(tr);
      }
    }
  });
}

function makeRows(cls, a, b, aStart, bStart) {
  const rows = [];
  const maxLen = Math.max(a.length, b.length);
  for (let i = 0; i < maxLen; i++) {
    const tr = document.createElement('tr');
    tr.className = cls;
    tr.innerHTML =
      `<td class="ln">${i < a.length ? aStart + i : ''}</td>` +
      `<td class="code">${esc(a[i] ?? '')}</td>` +
      `<td class="ln">${i < b.length ? bStart + i : ''}</td>` +
      `<td class="code">${esc(b[i] ?? '')}</td>`;
    rows.push(tr);
  }
  return rows;
}

function emitRows(tbody, cls, a, b, aStart, bStart) {
  makeRows(cls, a, b, aStart, bStart).forEach(r => tbody.appendChild(r));
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

document.getElementById('btn-compare').addEventListener('click', compareFiles);
init();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence default request logging

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if path == "/" or path == "/index.html":
            self.send_html(HTML)

        elif path == "/api/groups":
            groups = group_files(PGM_DIR)
            self.send_json({
                "pgm_dir": str(PGM_DIR),
                "groups": {k: v for k, v in groups.items()},
            })

        elif path == "/api/compare":
            fa = params.get("a", "")
            fb = params.get("b", "")
            if not fa or not fb:
                self.send_json({"error": "Missing parameters a and b"}, 400)
                return
            # Basic path traversal guard
            for name in (fa, fb):
                if ".." in name or "/" in name or "\\" in name:
                    self.send_json({"error": "Invalid filename"}, 400)
                    return
            lines_a = read_file_lines(PGM_DIR, fa)
            lines_b = read_file_lines(PGM_DIR, fb)
            result = compute_diff(lines_a, lines_b, fa, fb)
            self.send_json(result)

        else:
            self.send_response(404)
            self.end_headers()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not PGM_DIR.exists():
      print(f"[WARN] program folder not found at: {PGM_DIR}")
      print("       Set env var PGM_DIR to your folder path.")
    else:
        print(f"[INFO] Serving files from: {PGM_DIR}")

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"[INFO] Server running at {url}")
    print("       Press Ctrl+C to stop.\n")

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped.")


if __name__ == "__main__":
    main()
