#!/usr/bin/env python3
"""Fast, secure, and clean file comparator (2 or 3 files).

Compares two or three versions of the same file and reports changes between each pair.
Works with text and binary files.

Usage:
  python tools/three_file_comparator.py file_v1.txt file_v2.txt
  python tools/three_file_comparator.py file_v1.txt file_v2.txt file_v3.txt
  python tools/three_file_comparator.py a b c --show-diff --context 5
  python tools/three_file_comparator.py a b c --json
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


CHUNK_SIZE = 1024 * 1024  # 1 MB
DEFAULT_MAX_SIZE_MB = 50


@dataclass
class FileInfo:
    path: Path
    size: int
    sha256: str
    is_binary: bool
    lines: List[str] | None


@dataclass
class PairComparison:
    left: Path
    right: Path
    changed: bool
    similarity: float | None
    added_lines: int | None
    removed_lines: int | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two or three versions of a file (fast, secure, clean output)."
    )
    parser.add_argument("file1", type=Path, help="Path to version 1")
    parser.add_argument("file2", type=Path, help="Path to version 2")
    parser.add_argument("file3", nargs="?", type=Path, default=None, help="Path to version 3 (optional)")

    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Show unified diff for each pair (text files only).",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Diff context lines when --show-diff is set (default: 3).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    parser.add_argument(
        "--strip-trailing-space",
        action="store_true",
        help="Ignore trailing spaces in text comparisons.",
    )
    parser.add_argument(
        "--strip-line-numbers",
        action="store_true",
        help="Strip leading sequence numbers (e.g. '010\\t', '020 ') from each line before comparing.",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=DEFAULT_MAX_SIZE_MB,
        help=f"Refuse to load text content above this size in MB (default: {DEFAULT_MAX_SIZE_MB}).",
    )
    parser.add_argument(
        "--allow-large",
        action="store_true",
        help="Allow loading large files beyond --max-size-mb.",
    )

    return parser.parse_args()


def validate_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def detect_binary(path: Path) -> bool:
    with path.open("rb") as stream:
        sample = stream.read(8000)
    return b"\x00" in sample


LEADING_NUMBER_RE = re.compile(r"^\s*\d{2,6}\s")


def load_text_lines(
    path: Path,
    strip_trailing_space: bool,
    max_size_mb: int,
    allow_large: bool,
    strip_line_numbers: bool = False,
) -> List[str]:
    size = path.stat().st_size
    if not allow_large and size > max_size_mb * 1024 * 1024:
        raise ValueError(
            f"File too large for safe text diff ({size} bytes): {path}. "
            f"Use --allow-large to override."
        )

    with path.open("rb") as stream:
        data = stream.read()

    text = data.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines(keepends=True)

    if strip_trailing_space:
        lines = [line.rstrip(" \t") + ("\n" if line.endswith("\n") else "") for line in lines]

    if strip_line_numbers:
        lines = [LEADING_NUMBER_RE.sub("", line) for line in lines]

    return lines


def analyze_file(
    path: Path,
    strip_trailing_space: bool,
    max_size_mb: int,
    allow_large: bool,
    strip_line_numbers: bool = False,
) -> FileInfo:
    validate_path(path)
    size = path.stat().st_size
    file_hash = sha256_of_file(path)
    is_binary = detect_binary(path)

    lines: List[str] | None = None
    if not is_binary:
        lines = load_text_lines(path, strip_trailing_space, max_size_mb, allow_large, strip_line_numbers)

    return FileInfo(path=path, size=size, sha256=file_hash, is_binary=is_binary, lines=lines)


def compare_pair(left: FileInfo, right: FileInfo) -> PairComparison:
    changed = left.sha256 != right.sha256

    if left.is_binary or right.is_binary:
        return PairComparison(
            left=left.path,
            right=right.path,
            changed=changed,
            similarity=None,
            added_lines=None,
            removed_lines=None,
        )

    assert left.lines is not None and right.lines is not None

    matcher = difflib.SequenceMatcher(a=left.lines, b=right.lines, autojunk=False)
    similarity = matcher.ratio() * 100

    added = 0
    removed = 0
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "insert":
            added += j2 - j1
        elif op == "delete":
            removed += i2 - i1
        elif op == "replace":
            removed += i2 - i1
            added += j2 - j1

    return PairComparison(
        left=left.path,
        right=right.path,
        changed=changed,
        similarity=similarity,
        added_lines=added,
        removed_lines=removed,
    )


def pairwise(items: List[FileInfo]) -> Iterable[Tuple[FileInfo, FileInfo]]:
    if len(items) == 2:
        return ((items[0], items[1]),)
    return ((items[0], items[1]), (items[1], items[2]), (items[0], items[2]))


def unified_diff_text(left: FileInfo, right: FileInfo, context: int) -> str:
    if left.is_binary or right.is_binary:
        return "[Binary file(s): unified text diff skipped]"

    assert left.lines is not None and right.lines is not None

    diff = difflib.unified_diff(
        left.lines,
        right.lines,
        fromfile=str(left.path),
        tofile=str(right.path),
        n=context,
        lineterm="",
    )
    rendered = "\n".join(diff)
    return rendered if rendered.strip() else "[No textual diff]"


def format_human_summary(files: List[FileInfo], pairs: List[PairComparison]) -> str:
    lines: List[str] = []

    lines.append("=== Files ===")
    for info in files:
        kind = "binary" if info.is_binary else "text"
        lines.append(
            f"- {info.path} | {kind} | {info.size} bytes | sha256={info.sha256[:16]}..."
        )

    lines.append("")
    lines.append("=== Pairwise Changes ===")

    for p in pairs:
        base = f"- {p.left.name} -> {p.right.name}: {'CHANGED' if p.changed else 'IDENTICAL'}"
        if p.similarity is None:
            lines.append(base + " (binary compare by hash)")
        else:
            lines.append(
                base
                + f" | similarity={p.similarity:.2f}% | +{p.added_lines} / -{p.removed_lines} lines"
            )

    changed_count = sum(1 for p in pairs if p.changed)
    total_pairs = len(pairs)
    lines.append("")
    lines.append(f"Overall: {changed_count}/{total_pairs} pairs have changes.")

    return "\n".join(lines)


def format_json(files: List[FileInfo], pairs: List[PairComparison], show_diff: bool, context: int) -> str:
    payload = {
        "files": [
            {
                "path": str(f.path),
                "size": f.size,
                "type": "binary" if f.is_binary else "text",
                "sha256": f.sha256,
            }
            for f in files
        ],
        "comparisons": [
            {
                "left": str(p.left),
                "right": str(p.right),
                "changed": p.changed,
                "similarity_percent": None if p.similarity is None else round(p.similarity, 4),
                "added_lines": p.added_lines,
                "removed_lines": p.removed_lines,
            }
            for p in pairs
        ],
    }

    if show_diff:
        payload["diffs"] = []
        mapping = {}
        for a, b in pairwise(files):
            mapping[(a.path, b.path)] = (a, b)
        for p in pairs:
            left, right = mapping[(p.left, p.right)]
            payload["diffs"].append(
                {
                    "left": str(p.left),
                    "right": str(p.right),
                    "diff": unified_diff_text(left, right, context),
                }
            )

    return json.dumps(payload, indent=2, ensure_ascii=False)


def main() -> int:
    args = parse_args()

    paths = [args.file1, args.file2]
    if args.file3 is not None:
        paths.append(args.file3)

    try:
        files = [
            analyze_file(
                path,
                strip_trailing_space=args.strip_trailing_space,
                max_size_mb=args.max_size_mb,
                allow_large=args.allow_large,
                strip_line_numbers=args.strip_line_numbers,
            )
            for path in paths
        ]
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    pairs = [compare_pair(a, b) for a, b in pairwise(files)]

    if args.json:
        print(format_json(files, pairs, show_diff=args.show_diff, context=args.context))
    else:
        print(format_human_summary(files, pairs))

        if args.show_diff:
            print("\n=== Detailed Diffs ===")
            for a, b in pairwise(files):
                print(f"\n--- {a.path.name} -> {b.path.name} ---")
                print(unified_diff_text(a, b, args.context))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
