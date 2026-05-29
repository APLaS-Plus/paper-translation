#!/usr/bin/env python3
"""Download a paper PDF from arXiv by ID.

Usage:
    python download_paper.py <arxiv_id> [--output <dir>]

Example:
    python download_paper.py 2502.12391
    python download_paper.py 2502.12391 -o ~/Desktop/论文阅读/翻译
"""

import argparse
import sys
from pathlib import Path
from urllib.request import urlretrieve


ARXIV_PDF = "https://arxiv.org/pdf"


def main():
    parser = argparse.ArgumentParser(description="Download a paper PDF from arXiv")
    parser.add_argument("arxiv_id", help="arXiv ID, e.g. 2502.12391 or 2502.12391v2")
    parser.add_argument(
        "--output", "-o", type=Path, default=Path.cwd(),
        help="Output directory (default: current directory)"
    )
    args = parser.parse_args()

    paper_id = args.arxiv_id
    url = f"{ARXIV_PDF}/{paper_id}"

    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Strip version suffix for the output filename
    base_id = paper_id.split("v")[0]
    out_path = out_dir / f"{base_id}.pdf"

    if out_path.exists():
        print(f"Already exists: {out_path}")
        return

    print(f"Downloading {url} ...")
    try:
        urlretrieve(url, out_path)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)

    size_kb = out_path.stat().st_size / 1024
    print(f"Saved: {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
