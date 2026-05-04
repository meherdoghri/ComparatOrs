#!/usr/bin/env python3
"""Single-file local comparator app. Just run: python server.py
Opens the comparator in your default browser. No other files needed."""

import http.server
import threading
import webbrowser

PORT = 8080

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>File Comparator (2 or 3 files)</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel2: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --line: #374151;
      --diff: #7c2d12;
      --diff-soft: #451a03;
      --same: #0b1324;
      --added-bg: #052e16;
      --added-border: #16a34a;
      --modified-bg: #451a03;
      --modified-border: #ea580c;
      --deleted-bg: #450a0a;
      --deleted-border: #ef4444;
      --accent: #2563eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Segoe UI, Roboto, Arial, sans-serif;
    }
    .top {
      padding: 12px;
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      background: var(--panel);
      z-index: 10;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      align-items: stretch;
      transition: grid-template-columns 0.2s;
    }
    .controls.mode-2 {
      grid-template-columns: 1fr 1fr;
    }
    .file-box {
      display: grid;
      gap: 6px;
      min-width: 220px;
    }
    label { font-size: 12px; color: var(--muted); }
    input[type="text"] {
      width: 100%;
      padding: 6px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel2);
      color: var(--text);
    }
    textarea {
      width: 100%;
      min-height: 120px;
      resize: vertical;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel2);
      color: var(--text);
      font-family: Consolas, Menlo, monospace;
      font-size: 12px;
      line-height: 1.4;
    }
    .actions {
      margin-top: 8px;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .btn {
      height: 34px;
      padding: 0 14px;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .row2 {
      margin-top: 8px;
      display: flex;
      gap: 14px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
    }
    .warn {
      color: #fca5a5;
      font-size: 12px;
      font-weight: 600;
    }
    .summary {
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 600;
    }
    .verdict {
      font-size: 12px;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid transparent;
    }
    .verdict.ok {
      color: #86efac;
      background: #052e16;
      border-color: #166534;
    }
    .verdict.fail {
      color: #fecaca;
      background: #450a0a;
      border-color: #991b1b;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      height: calc(100vh - 120px);
      min-height: 360px;
      transition: grid-template-columns 0.2s;
    }
    .grid.mode-2 {
      grid-template-columns: 1fr 1fr;
    }
    .col {
      border-right: 1px solid var(--line);
      overflow: auto;
    }
    .col:last-child { border-right: none; }
    .head {
      position: sticky;
      top: 0;
      z-index: 5;
      background: var(--panel2);
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .line {
      display: grid;
      grid-template-columns: 60px 1fr;
      gap: 8px;
      border-bottom: 1px solid rgba(55, 65, 81, 0.35);
      font-family: Consolas, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre;
      min-height: 20px;
      align-items: start;
      padding: 2px 8px;
    }
    .line.same { background: var(--same); }
    .line.modified { background: var(--modified-bg); box-shadow: inset 2px 0 0 var(--modified-border); }
    .line.added { background: var(--added-bg); box-shadow: inset 2px 0 0 var(--added-border); }
    .line.deleted { background: var(--deleted-bg); box-shadow: inset 2px 0 0 var(--deleted-border); }
    .line.gap { background: #1f2937; }
    .line.verified { outline: 1px solid #0891b2; outline-offset: -1px; }
    .line.missing { outline: 1px solid #facc15; outline-offset: -1px; }
    .line-number {
      color: var(--muted);
      user-select: none;
      text-align: right;
      padding-right: 6px;
      border-right: 1px solid rgba(156,163,175,0.25);
    }
    .line-text {
      overflow: visible;
      padding-left: 2px;
    }
    .empty {
      color: #6b7280;
      font-style: italic;
    }
    .legend {
      display: inline-flex;
      gap: 8px;
      align-items: center;
    }
    .swatch { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
    .sw-same { background: var(--same); border: 1px solid var(--line); }
    .sw-diff { background: var(--diff-soft); border: 1px solid #92400e; }
    .hidden { display: none !important; }
    .mode-toggle {
      display: flex;
      gap: 0;
      margin-bottom: 8px;
    }
    .mode-toggle button {
      padding: 6px 16px;
      border: 1px solid var(--accent);
      background: var(--panel2);
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
    }
    .mode-toggle button:first-child {
      border-radius: 6px 0 0 6px;
    }
    .mode-toggle button:last-child {
      border-radius: 0 6px 6px 0;
    }
    .mode-toggle button.active {
      background: var(--accent);
      color: white;
    }
  </style>
</head>
<body>
  <div class="top">
    <div class="mode-toggle">
      <button id="mode2Btn" type="button">2 Files</button>
      <button id="mode3Btn" type="button" class="active">3 Files</button>
    </div>
    <div class="controls" id="controlsGrid">
      <div class="file-box">
        <input id="name1" type="text" value="Suite 7" />
        <label>Paste content of Version 1</label>
        <textarea id="text1" placeholder="Paste file content here..."></textarea>
      </div>
      <div class="file-box">
        <input id="name2" type="text" value="Suite 7 Actuelle" />
        <label>Paste content of Version 2</label>
        <textarea id="text2" placeholder="Paste file content here..."></textarea>
      </div>
      <div class="file-box" id="fileBox3">
        <input id="name3" type="text" value="4YOU" />
        <label>Paste content of Version 3</label>
        <textarea id="text3" placeholder="Paste file content here..."></textarea>
      </div>
    </div>
    <div class="actions">
      <button id="compareBtn" class="btn" disabled>Compare</button>
      <button id="checkDeltaBtn" class="btn" type="button" disabled style="background:#065f46;border-color:#047857;" title="Only available in 3-file mode">Check Delta In V3</button>
      <button id="clearBtn" class="btn" type="button" style="background:#374151;border-color:#4b5563;">Clear</button>
      <span id="verdict" class="verdict"></span>
    </div>
    <div class="row2">
      <label><input id="onlyDiff" type="checkbox" /> Show only different lines</label>
      <label><input id="onlyDelta" type="checkbox" /> Show only V1->V2 delta</label>
      <label><input id="ignoreTrailing" type="checkbox" /> Ignore trailing spaces</label>
      <label><input id="stripLineNumbers" type="checkbox" /> Strip leading line numbers</label>
      <span class="legend"><span class="swatch sw-same"></span> same</span>
      <span class="legend"><span class="swatch" style="background:var(--added-bg);border:1px solid var(--added-border);"></span> added</span>
      <span class="legend"><span class="swatch" style="background:var(--modified-bg);border:1px solid var(--modified-border);"></span> modified</span>
      <span class="legend"><span class="swatch" style="background:var(--deleted-bg);border:1px solid var(--deleted-border);"></span> deleted</span>
      <span class="legend"><span class="swatch" style="background:transparent;border:1px solid #0891b2;"></span> verified in V3</span>
      <span class="legend"><span class="swatch" style="background:transparent;border:1px solid #facc15;"></span> missing in V3</span>
      <span id="stats"></span>
      <span id="deltaSummary" class="summary"></span>
      <span id="warning" class="warn"></span>
    </div>
  </div>

  <div class="grid" id="gridContainer">
    <div class="col" id="col1"><div class="head" id="head1">File 1</div><div id="body1"></div></div>
    <div class="col" id="col2"><div class="head" id="head2">File 2</div><div id="body2"></div></div>
    <div class="col" id="col3"><div class="head" id="head3">File 3</div><div id="body3"></div></div>
  </div>

  <script>
    const name1Input = document.getElementById('name1');
    const name2Input = document.getElementById('name2');
    const name3Input = document.getElementById('name3');
    const text1Input = document.getElementById('text1');
    const text2Input = document.getElementById('text2');
    const text3Input = document.getElementById('text3');
    const compareBtn = document.getElementById('compareBtn');
    const checkDeltaBtn = document.getElementById('checkDeltaBtn');
    const clearBtn = document.getElementById('clearBtn');
    const onlyDiff = document.getElementById('onlyDiff');
    const onlyDelta = document.getElementById('onlyDelta');
    const ignoreTrailing = document.getElementById('ignoreTrailing');
    const stripLineNumbers = document.getElementById('stripLineNumbers');
    const mode2Btn = document.getElementById('mode2Btn');
    const mode3Btn = document.getElementById('mode3Btn');
    const fileBox3 = document.getElementById('fileBox3');
    const controlsGrid = document.getElementById('controlsGrid');
    const gridContainer = document.getElementById('gridContainer');

    let currentMode = 3;

    const head1 = document.getElementById('head1');
    const head2 = document.getElementById('head2');
    const head3 = document.getElementById('head3');
    const body1 = document.getElementById('body1');
    const body2 = document.getElementById('body2');
    const body3 = document.getElementById('body3');
    const stats = document.getElementById('stats');
    const deltaSummary = document.getElementById('deltaSummary');
    const warning = document.getElementById('warning');
    const verdict = document.getElementById('verdict');

    const col1 = document.getElementById('col1');
    const col2 = document.getElementById('col2');
    const col3 = document.getElementById('col3');

    let syncLock = false;
    let cacheRows = [];
    const MAX_EXACT_COMPLEXITY = 12_000_000;

    function normalize(text) {
      let lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
      if (lines.length > 1 && lines[lines.length - 1] === '') {
        lines.pop();
      }
      if (stripLineNumbers.checked) {
        lines = lines.map(line => line.replace(/^\s*\d{2,6}\s/, ''));
      }
      return lines;
    }

    function markEnabled() {
      const has1 = text1Input.value.trim().length > 0;
      const has2 = text2Input.value.trim().length > 0;
      const has3 = text3Input.value.trim().length > 0;
      if (currentMode === 2) {
        const enabled = has1 && has2;
        compareBtn.disabled = !enabled;
        checkDeltaBtn.disabled = true;
      } else {
        const enabled = has1 && has2 && has3;
        compareBtn.disabled = !enabled;
        checkDeltaBtn.disabled = !enabled;
      }
    }

    function clearVerdict() {
      verdict.textContent = '';
      verdict.className = 'verdict';
    }

    function evaluateDeltaPresence(rows) {
      let totalDeltaRows = 0;
      let presentDeltaRows = 0;
      let missingDeltaRows = 0;
      const sampleMissing = [];

      for (const row of rows) {
        if (!row.isDelta) continue;

        totalDeltaRows++;
        if (row.deltaPresentInV3) {
          presentDeltaRows++;
        } else {
          missingDeltaRows++;
          if (sampleMissing.length < 5) {
            if (row.deltaKind === 'deleted') {
              sampleMissing.push('Deleted block near V1 line ' + row.n1);
            } else {
              sampleMissing.push('V2 line ' + row.n2);
            }
          }
        }
      }

      return { totalDeltaRows, presentDeltaRows, missingDeltaRows, sampleMissing };
    }

    function showVerdict() {
      if (cacheRows.length === 0) {
        clearVerdict();
        deltaSummary.textContent = '';
        return;
      }

      const { totalDeltaRows, presentDeltaRows, missingDeltaRows, sampleMissing } = evaluateDeltaPresence(cacheRows);
      const v1Name = (name1Input.value || 'Version 1').trim();
      const v2Name = (name2Input.value || 'Version 2').trim();
      const v3Name = (name3Input.value || 'Version 3').trim();

      deltaSummary.textContent = totalDeltaRows === 0
        ? 'delta rows: 0'
        : 'delta rows: ' + totalDeltaRows + ' | verified in ' + v3Name + ': ' + presentDeltaRows + ' | missing in ' + v3Name + ': ' + missingDeltaRows;

      if (totalDeltaRows === 0) {
        verdict.className = 'verdict ok';
        verdict.textContent = 'No delta detected between ' + v1Name + ' and ' + v2Name + '.';
        return;
      }

      if (missingDeltaRows === 0) {
        verdict.className = 'verdict ok';
        verdict.textContent = 'PASS: ' + v3Name + ' contains all delta rows from ' + v1Name + ' -> ' + v2Name + ' (' + presentDeltaRows + '/' + totalDeltaRows + ').';
      } else {
        verdict.className = 'verdict fail';
        const details = sampleMissing.length ? ' Missing: ' + sampleMissing.join(', ') + '.' : '';
        verdict.textContent = 'FAIL: ' + v3Name + ' is missing ' + missingDeltaRows + ' of ' + totalDeltaRows + ' delta rows from ' + v1Name + ' -> ' + v2Name + '.' + details;
      }
    }

    function buildLine(lineNumber, text, cellKind, extraClass) {
      extraClass = extraClass || '';
      const row = document.createElement('div');
      row.className = 'line ' + cellKind + (extraClass ? ' ' + extraClass : '');

      const num = document.createElement('div');
      num.className = 'line-number';
      num.textContent = lineNumber > 0 ? String(lineNumber) : '';

      const txt = document.createElement('div');
      txt.className = 'line-text';
      txt.textContent = text === '' ? (cellKind === 'deleted' ? '\u2205 deleted' : ' ') : text;
      if (lineNumber === 0) txt.classList.add('empty');

      row.appendChild(num);
      row.appendChild(txt);
      return row;
    }

    function render(rows) {
      body1.innerHTML = '';
      body2.innerHTML = '';
      body3.innerHTML = '';

      let sameCount = 0;
      let diffCount = 0;

      for (const row of rows) {
        if (onlyDiff.checked && !row.isDiff) continue;
        if (onlyDelta.checked && !row.isDelta) continue;

        body1.appendChild(buildLine(row.n1, row.t1, row.k1));
        body2.appendChild(buildLine(row.n2, row.t2, row.k2));
        if (currentMode === 3) {
          body3.appendChild(buildLine(row.n3, row.t3, row.k3, row.v3StatusClass));
        }

        if (row.isDiff) diffCount++; else sameCount++;
      }

      stats.textContent = 'same lines: ' + sameCount + ' | different lines: ' + diffCount;
    }

    function buildLcsTable(a, b) {
      const n = a.length;
      const m = b.length;
      const dp = Array.from({ length: n + 1 }, function() { return new Uint32Array(m + 1); });

      for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
          if (a[i] === b[j]) {
            dp[i][j] = dp[i + 1][j + 1] + 1;
          } else {
            dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
          }
        }
      }
      return dp;
    }

    function compareLine(a, b) {
      if (ignoreTrailing.checked) {
        return a.trimEnd() === b.trimEnd();
      }
      return a === b;
    }

    function levenshteinDistance(a, b) {
      const m = a.length;
      const n = b.length;
      const dp = Array.from({ length: m + 1 }, function() { return new Uint32Array(n + 1); });
      for (let i = 0; i <= m; i++) dp[i][0] = i;
      for (let j = 0; j <= n; j++) dp[0][j] = j;
      for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
          if (a[i - 1] === b[j - 1]) {
            dp[i][j] = dp[i - 1][j - 1];
          } else {
            dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
          }
        }
      }
      return dp[m][n];
    }

    function isFuzzyMatch(a, b) {
      if (a === '' || b === '') return false;
      const maxLen = Math.max(a.length, b.length);
      const threshold = Math.max(2, Math.ceil(maxLen * 0.1));
      return levenshteinDistance(a, b) <= threshold;
    }

    function getDeltaMeta(n1, n2, n3, t1, t2, t3) {
      if (n2 > 0) {
        if (n1 === 0) {
          const presentInV3 = compareLine(t2, t3);
          return {
            isDelta: true,
            deltaKind: 'added',
            deltaPresentInV3: presentInV3,
            k2: 'added',
            v3StatusClass: presentInV3 ? 'verified' : 'missing',
          };
        }

        if (!compareLine(t1, t2)) {
          const presentInV3 = compareLine(t2, t3);
          return {
            isDelta: true,
            deltaKind: 'modified',
            deltaPresentInV3: presentInV3,
            k2: 'modified',
            v3StatusClass: presentInV3 ? 'verified' : 'missing',
          };
        }

        return {
          isDelta: false,
          deltaKind: 'none',
          deltaPresentInV3: true,
          k2: 'same',
          v3StatusClass: '',
        };
      }

      if (n1 > 0) {
        const presentInV3 = n3 === 0;
        return {
          isDelta: true,
          deltaKind: 'deleted',
          deltaPresentInV3: presentInV3,
          k2: 'gap',
          v3StatusClass: presentInV3 ? 'verified' : 'missing',
        };
      }

      return {
        isDelta: false,
        deltaKind: 'none',
        deltaPresentInV3: true,
        k2: 'gap',
        v3StatusClass: '',
      };
    }

    function alignOtherToBase(baseLines, otherLines) {
      const n = baseLines.length;
      const m = otherLines.length;

      const insertBefore = Array.from({ length: n + 1 }, function() { return []; });
      const mapOnBase = new Array(n).fill(null);

      const complexity = n * m;
      if (complexity > MAX_EXACT_COMPLEXITY) {
        throw new Error('Exact alignment too large (' + n + 'x' + m + ' lines). Split file or compare smaller blocks.');
      }

      const dp = buildLcsTable(baseLines, otherLines);

      let i = 0;
      let j = 0;
      while (i < n && j < m) {
        if (compareLine(baseLines[i], otherLines[j])) {
          mapOnBase[i] = j;
          i++;
          j++;
        } else if (isFuzzyMatch(baseLines[i], otherLines[j])) {
          mapOnBase[i] = j;
          i++;
          j++;
        } else if (dp[i + 1][j] >= dp[i][j + 1]) {
          mapOnBase[i] = null;
          i++;
        } else {
          insertBefore[i].push(j);
          j++;
        }
      }

      while (i < n) {
        mapOnBase[i] = null;
        i++;
      }
      while (j < m) {
        insertBefore[n].push(j);
        j++;
      }

      return { insertBefore: insertBefore, mapOnBase: mapOnBase };
    }

    function alignInsertedBuckets(lines1, idxs1, lines3, idxs3) {
      const seq1 = idxs1.map(function(i) { return lines1[i]; });
      const seq3 = idxs3.map(function(i) { return lines3[i]; });

      const n = seq1.length;
      const m = seq3.length;
      if (n === 0 && m === 0) return [];
      if (n === 0) return idxs3.map(function(i3) { return { i1: null, i3: i3 }; });
      if (m === 0) return idxs1.map(function(i1) { return { i1: i1, i3: null }; });

      const complexity = n * m;
      if (complexity > MAX_EXACT_COMPLEXITY) {
        throw new Error('Exact inserted-block alignment too large (' + n + 'x' + m + ' lines). Split file or compare smaller blocks.');
      }

      const dp = buildLcsTable(seq1, seq3);
      const rows = [];
      let i = 0;
      let j = 0;

      while (i < n && j < m) {
        if (compareLine(seq1[i], seq3[j])) {
          rows.push({ i1: idxs1[i], i3: idxs3[j] });
          i++;
          j++;
        } else if (dp[i + 1][j] >= dp[i][j + 1]) {
          rows.push({ i1: idxs1[i], i3: null });
          i++;
        } else {
          rows.push({ i1: null, i3: idxs3[j] });
          j++;
        }
      }

      while (i < n) {
        rows.push({ i1: idxs1[i], i3: null });
        i++;
      }
      while (j < m) {
        rows.push({ i1: null, i3: idxs3[j] });
        j++;
      }

      return rows;
    }

    function compare2(lines1, lines2) {
      const base = lines2;
      const a1 = alignOtherToBase(base, lines1);
      const rows = [];
      const baseLen = base.length;

      for (let baseIndex = 0; baseIndex <= baseLen; baseIndex++) {
        const ins1 = a1.insertBefore[baseIndex];

        for (let idx = 0; idx < ins1.length; idx++) {
          const idx1 = ins1[idx];
          const t1 = lines1[idx1];
          rows.push({
            n1: idx1 + 1, n2: 0, n3: 0,
            t1: t1, t2: '', t3: '',
            isDiff: true,
            isDelta: false, deltaKind: 'none', deltaPresentInV3: true,
            k1: 'added', k2: 'gap', k3: 'gap',
            v3StatusClass: '',
          });
        }

        if (baseIndex < baseLen) {
          const idx1 = a1.mapOnBase[baseIndex];
          const t1 = idx1 === null ? '' : lines1[idx1];
          const t2 = base[baseIndex];
          const isDiff = !compareLine(t1, t2);
          const k1 = idx1 === null ? 'deleted' : (compareLine(t1, t2) ? 'same' : 'modified');
          const k2 = idx1 === null ? 'added' : (compareLine(t1, t2) ? 'same' : 'modified');

          rows.push({
            n1: idx1 === null ? 0 : idx1 + 1,
            n2: baseIndex + 1,
            n3: 0,
            t1: t1, t2: t2, t3: '',
            isDiff: isDiff,
            isDelta: false, deltaKind: 'none', deltaPresentInV3: true,
            k1: k1, k2: k2, k3: 'gap',
            v3StatusClass: '',
          });
        }
      }

      return rows;
    }

    function compare3(lines1, lines2, lines3) {
      const base = lines2;
      const a1 = alignOtherToBase(base, lines1);
      const a3 = alignOtherToBase(base, lines3);

      const rows = [];
      const baseLen = base.length;

      for (let baseIndex = 0; baseIndex <= baseLen; baseIndex++) {
        const ins1 = a1.insertBefore[baseIndex];
        const ins3 = a3.insertBefore[baseIndex];
        const alignedInsertRows = alignInsertedBuckets(lines1, ins1, lines3, ins3);

        for (let ai = 0; ai < alignedInsertRows.length; ai++) {
          const pair = alignedInsertRows[ai];
          const idx1 = pair.i1;
          const idx3 = pair.i3;

          const t1 = idx1 === null ? '' : lines1[idx1];
          const t2 = '';
          const t3 = idx3 === null ? '' : lines3[idx3];

          const isDiff = !(compareLine(t1, t2) && compareLine(t2, t3));
          const deltaMeta = getDeltaMeta(
            idx1 === null ? 0 : idx1 + 1,
            0,
            idx3 === null ? 0 : idx3 + 1,
            t1,
            t2,
            t3
          );

          rows.push({
            n1: idx1 === null ? 0 : idx1 + 1,
            n2: 0,
            n3: idx3 === null ? 0 : idx3 + 1,
            t1: t1, t2: t2, t3: t3,
            isDiff: isDiff,
            isDelta: deltaMeta.isDelta,
            deltaKind: deltaMeta.deltaKind,
            deltaPresentInV3: deltaMeta.deltaPresentInV3,
            k1: idx1 === null ? 'gap' : 'added',
            k2: deltaMeta.k2,
            k3: idx3 === null ? 'gap' : 'added',
            v3StatusClass: deltaMeta.v3StatusClass,
          });
        }

        if (baseIndex < baseLen) {
          const idx1 = a1.mapOnBase[baseIndex];
          const idx3 = a3.mapOnBase[baseIndex];
          const t1 = idx1 === null ? '' : lines1[idx1];
          const t2 = base[baseIndex];
          const t3 = idx3 === null ? '' : lines3[idx3];

          const isDiff = !(compareLine(t1, t2) && compareLine(t2, t3));
          const deltaMeta = getDeltaMeta(
            idx1 === null ? 0 : idx1 + 1,
            baseIndex + 1,
            idx3 === null ? 0 : idx3 + 1,
            t1,
            t2,
            t3
          );

          const k1 = idx1 === null ? 'deleted' : (compareLine(t1, t2) ? 'same' : 'modified');
          const k3 = idx3 === null ? 'deleted' : (compareLine(t3, t2) ? 'same' : 'modified');

          rows.push({
            n1: idx1 === null ? 0 : idx1 + 1,
            n2: baseIndex + 1,
            n3: idx3 === null ? 0 : idx3 + 1,
            t1: t1, t2: t2, t3: t3,
            isDiff: isDiff,
            isDelta: deltaMeta.isDelta,
            deltaKind: deltaMeta.deltaKind,
            deltaPresentInV3: deltaMeta.deltaPresentInV3,
            k1: k1,
            k2: deltaMeta.k2,
            k3: k3,
            v3StatusClass: deltaMeta.v3StatusClass,
          });
        }
      }

      return rows;
    }

    function syncScroll(source, targets) {
      if (syncLock) return;
      syncLock = true;
      for (let ti = 0; ti < targets.length; ti++) {
        targets[ti].scrollTop = source.scrollTop;
        targets[ti].scrollLeft = source.scrollLeft;
      }
      syncLock = false;
    }

    col1.addEventListener('scroll', function() { syncScroll(col1, currentMode === 3 ? [col2, col3] : [col2]); });
    col2.addEventListener('scroll', function() { syncScroll(col2, currentMode === 3 ? [col1, col3] : [col1]); });
    col3.addEventListener('scroll', function() { syncScroll(col3, [col1, col2]); });

    [text1Input, text2Input, text3Input].forEach(function(input) { input.addEventListener('input', markEnabled); });

    onlyDiff.addEventListener('change', function() { render(cacheRows); });
    onlyDelta.addEventListener('change', function() { render(cacheRows); });
    ignoreTrailing.addEventListener('change', function() {
      if (cacheRows.length > 0) {
        compareBtn.click();
      }
    });
    stripLineNumbers.addEventListener('change', function() {
      if (cacheRows.length > 0) {
        compareBtn.click();
      }
    });
    checkDeltaBtn.addEventListener('click', function() { showVerdict(); });

    function setMode(mode) {
      currentMode = mode;
      if (mode === 2) {
        mode2Btn.classList.add('active');
        mode3Btn.classList.remove('active');
        fileBox3.classList.add('hidden');
        col3.classList.add('hidden');
        controlsGrid.classList.add('mode-2');
        gridContainer.classList.add('mode-2');
        onlyDelta.parentElement.classList.add('hidden');
        checkDeltaBtn.classList.add('hidden');
      } else {
        mode3Btn.classList.add('active');
        mode2Btn.classList.remove('active');
        fileBox3.classList.remove('hidden');
        col3.classList.remove('hidden');
        controlsGrid.classList.remove('mode-2');
        gridContainer.classList.remove('mode-2');
        onlyDelta.parentElement.classList.remove('hidden');
        checkDeltaBtn.classList.remove('hidden');
      }
      markEnabled();
      clearVerdict();
      cacheRows = [];
      body1.innerHTML = '';
      body2.innerHTML = '';
      body3.innerHTML = '';
      stats.textContent = '';
      deltaSummary.textContent = '';
      warning.textContent = '';
    }

    mode2Btn.addEventListener('click', function() { setMode(2); });
    mode3Btn.addEventListener('click', function() { setMode(3); });

    clearBtn.addEventListener('click', function() {
      text1Input.value = '';
      text2Input.value = '';
      text3Input.value = '';
      head1.textContent = 'File 1';
      head2.textContent = 'File 2';
      head3.textContent = 'File 3';
      cacheRows = [];
      body1.innerHTML = '';
      body2.innerHTML = '';
      body3.innerHTML = '';
      stats.textContent = '';
      deltaSummary.textContent = '';
      warning.textContent = '';
      clearVerdict();
      markEnabled();
    });

    compareBtn.addEventListener('click', function() {
      const txt1 = text1Input.value;
      const txt2 = text2Input.value;
      const txt3 = text3Input.value;

      if (currentMode === 2) {
        if (!txt1.trim() || !txt2.trim()) return;
      } else {
        if (!txt1.trim() || !txt2.trim() || !txt3.trim()) return;
      }

      head1.textContent = (name1Input.value || 'File 1').trim();
      head2.textContent = (name2Input.value || 'File 2').trim();
      if (currentMode === 3) {
        head3.textContent = (name3Input.value || 'File 3').trim();
      }

      const lines1 = normalize(txt1);
      const lines2 = normalize(txt2);

      try {
        warning.textContent = '';
        if (currentMode === 2) {
          cacheRows = compare2(lines1, lines2);
        } else {
          const lines3 = normalize(txt3);
          cacheRows = compare3(lines1, lines2, lines3);
        }
        render(cacheRows);
        if (currentMode === 3) showVerdict();
      } catch (err) {
        cacheRows = [];
        body1.innerHTML = '';
        body2.innerHTML = '';
        body3.innerHTML = '';
        stats.textContent = '';
        warning.textContent = err instanceof Error ? err.message : 'Comparison failed.';
        clearVerdict();
      }
    });
  </script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"File Comparator running at {url}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
