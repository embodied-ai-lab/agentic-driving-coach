#!/usr/bin/env python3
"""Build the submission archive for Canvas.

Usage:
    python scripts/make_submission.py --groupid your_groupid \
        [--results results/...]...
        [--zip submission/group<groupid>_agentic-driving-coach.zip]

Included:
- submission/answers.md (your filled-in copy of answers_template.md)
- results/environment.txt if present
- from each named results directory: summary.json, manifest.json, run.csv,
  trace.jsonl, comparison.{csv,json}, and all PNG figures
- files you modified relative to git HEAD under src/, configs/, data/
  (detected with `git status`; skipped with a note when git is unavailable)

Never included: model weights, .venv, __pycache__, caches, sibling repos,
or any single file over 20 MB (a warning is printed instead).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 20 * 1024 * 1024
RESULT_PATTERNS = (
    "summary.json",
    "manifest.json",
    "run.csv",
    "trace.jsonl",
    "comparison.csv",
    "comparison.json",
    "*.png",
)
EXCLUDED_SUFFIXES = {".gguf", ".safetensors", ".sif", ".pyc"}


def _git_modified_files() -> list[Path] | None:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO, capture_output=True, text=True, timeout=10, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    paths: list[Path] = []
    for line in proc.stdout.splitlines():
        entry = line[3:].split(" -> ")[-1].strip().strip('"')
        path = REPO / entry
        if not path.is_file():
            continue
        if any(part in (".venv", "__pycache__", "results", "submission") for part in path.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        if entry.startswith(("src/", "configs/", "data/")):
            paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groupid", required=True, help="your group (names the zip)")
    parser.add_argument(
        "--results",
        action="append",
        type=Path,
        default=[],
        help="results directory to include (repeatable); default: all of results/",
    )
    parser.add_argument("--zip", type=Path, default=None, help="output zip path")
    args = parser.parse_args()

    out_zip = (
        args.zip
        or REPO / "submission" / f"group{args.groupid}_agentic-driving-coach.zip"
    )
    answers = REPO / "submission" / "answers.md"
    if not answers.exists():
        print(
            "ERROR: submission/answers.md not found.\n"
            "Copy submission/answers_template.md to submission/answers.md and fill it in.",
            file=sys.stderr,
        )
        return 2

    result_dirs = args.results or sorted(
        d for d in (REPO / "results").iterdir() if d.is_dir()
    )

    files: list[tuple[Path, str]] = [(answers, "answers.md")]
    env_txt = REPO / "results" / "environment.txt"
    if env_txt.exists():
        files.append((env_txt, "results/environment.txt"))

    for directory in result_dirs:
        for pattern in RESULT_PATTERNS:
            for path in sorted(directory.rglob(pattern)):
                files.append((path, str(path.relative_to(REPO))))

    modified = _git_modified_files()
    if modified is None:
        print("note: git not available; modified-source detection skipped "
              "(attach modified files manually if you changed any).")
    else:
        for path in modified:
            files.append((path, str(path.relative_to(REPO))))

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    skipped: list[str] = []
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in files:
            if arcname in seen:
                continue
            seen.add(arcname)
            if path.stat().st_size > MAX_FILE_BYTES:
                skipped.append(arcname)
                continue
            zf.write(path, arcname)

    print(f"wrote {out_zip} ({len(seen) - len(skipped)} files)")
    for name in sorted(seen - set(skipped)):
        print(f"  + {name}")
    for name in skipped:
        print(f"  ! skipped (over {MAX_FILE_BYTES // (1024 * 1024)} MB): {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
