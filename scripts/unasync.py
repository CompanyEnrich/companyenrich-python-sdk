"""Generates the sync client and its tests from the async sources.

Run with --check to fail if the generated files are out of date.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIRS = [
    (ROOT / "src" / "companyenrich" / "_async", ROOT / "src" / "companyenrich" / "_sync"),
    (ROOT / "tests" / "_async", ROOT / "tests" / "_sync"),
]
HEADER = "# Generated from the _async package by scripts/unasync.py. Do not edit.\n\n"
REPLACEMENTS = [
    (re.compile(r"\bAsync([A-Z]\w*)"), r"\1"),
    (re.compile(r"\basync (def|for|with)\b"), r"\1"),
    (re.compile(r"\bawait "), ""),
    (re.compile(r"\baclosing\b"), "closing"),
    (re.compile(r"\baclose\b"), "close"),
    (re.compile(r"\baread\b"), "read"),
    (re.compile(r"\baiter_bytes\b"), "iter_bytes"),
    (re.compile(r"__aenter__"), "__enter__"),
    (re.compile(r"__aexit__"), "__exit__"),
    (re.compile(r"\basyncio\.sleep\b"), "time.sleep"),
    (re.compile(r"^import asyncio$", re.MULTILINE), "import time"),
    (re.compile(r"\b_async\b"), "_sync"),
]


def transform(source: str) -> str:
    for pattern, replacement in REPLACEMENTS:
        source = pattern.sub(replacement, source)
    return HEADER + source


def expected_files() -> dict[Path, str]:
    return {
        target / path.relative_to(source): transform(path.read_text(encoding="utf-8"))
        for source, target in PAIRS
        for path in sorted(source.rglob("*.py"))
    }


def main() -> None:
    files = expected_files()
    if "--check" in sys.argv[1:]:
        stale = [
            path
            for path, content in files.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        for _, target in PAIRS:
            stale += [path for path in target.rglob("*.py") if path not in files]
        if stale:
            print("Out of date. Run scripts/unasync.py:", *stale, sep="\n  ")
            raise SystemExit(1)
        return

    for _, target in PAIRS:
        for path in target.rglob("*.py"):
            path.unlink()
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
