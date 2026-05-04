#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash tools/detect_missing_blocks.sh "S7 standard" "S7 Modified" "4YOU" "Result"

standard_file="${1:-S7 standard}"
modified_file="${2:-S7 Modified}"
target_file="${3:-4YOU}"
result_file="${4:-Result}"

tmp_standard="$(mktemp)"
tmp_modified="$(mktemp)"
tmp_target="$(mktemp)"
trap 'rm -f "$tmp_standard" "$tmp_modified" "$tmp_target"' EXIT

if [[ ! -f "$standard_file" ]]; then
  echo "ERROR: missing file: $standard_file" >&2
  exit 2
fi
if [[ ! -f "$modified_file" ]]; then
  echo "ERROR: missing file: $modified_file" >&2
  exit 2
fi
if [[ ! -f "$target_file" ]]; then
  echo "ERROR: missing file: $target_file" >&2
  exit 2
fi

# Fast deterministic exact checks
std_hash="$(sha256sum "$standard_file" | awk '{print $1}')"
mod_hash="$(sha256sum "$modified_file" | awk '{print $1}')"

# Clean visual diff inputs (no CRLF and expanded tabs)
sed 's/\r$//' "$standard_file" | expand -t 4 > "$tmp_standard"
sed 's/\r$//' "$modified_file" | expand -t 4 > "$tmp_modified"
sed 's/\r$//' "$target_file" | expand -t 4 > "$tmp_target"

{
  echo "CHECK 1: $standard_file -> $modified_file"
  if [[ "$std_hash" == "$mod_hash" ]]; then
    echo "Status: NO CHANGES"
    echo
    echo "SIDE BY SIDE: $standard_file | $modified_file"
    echo "(No differences)"
    echo
    echo "CHECK 2: skipped (no change in modified file)"
    echo "Missing blocks in $target_file: None"
    exit 0
  fi

  echo "Status: CHANGES DETECTED"
  echo "sha256($standard_file)=$std_hash"
  echo "sha256($modified_file)=$mod_hash"
  echo

  echo "SIDE BY SIDE: $standard_file | $modified_file"
  echo "Legend: | = changed line, < = only in left, > = only in right"
  echo "--------------------------------------------------------------------------------"
  if diff -y --suppress-common-lines -W 220 "$tmp_standard" "$tmp_modified"; then
    echo "(No differences)"
  fi
  echo

  echo "CHECK 2: $modified_file -> $target_file"

  # Missing lines in target are '-' lines when left=modified and right=target.
  # Ignore headers (--- / +++ / @@).
  missing_lines="$({ diff -u "$modified_file" "$target_file" || true; } | awk '
    /^--- / {next}
    /^\+\+\+ / {next}
    /^@@ / {next}
    /^-/ {print substr($0,2)}
  ')"

  meaningful_missing="$(printf '%s\n' "$missing_lines" | awk '{ line=$0; gsub(/[[:space:]]/, "", line); if (length(line) > 0) print $0 }')"

  if [[ -z "$meaningful_missing" ]]; then
    echo "Status: NO MISSING BLOCKS"
    echo "Missing blocks in $target_file: None"
  else
    echo "Status: MISSING BLOCKS FOUND"
    echo "Missing blocks in $target_file:"
    echo "$meaningful_missing"
  fi
  echo

  echo "SIDE BY SIDE: $modified_file | $target_file"
  echo "Legend: | = changed line, < = only in left, > = only in right"
  echo "--------------------------------------------------------------------------------"
  if diff -y --suppress-common-lines -W 220 "$tmp_modified" "$tmp_target"; then
    echo "(No differences)"
  fi
} > "$result_file"

echo "Done. Report written to: $result_file"
