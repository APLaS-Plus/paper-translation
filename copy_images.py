#!/usr/bin/env python3
"""Copy only referenced images from mineru_output/images/ to medias/.

Usage: python copy_images.py <paper_dir>
"""
import re, shutil, sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python copy_images.py <paper_dir>")
        sys.exit(1)
    paper_dir = Path(sys.argv[1]).resolve()
    full_md = paper_dir / "mineru_output" / "full.md"
    img_src = paper_dir / "mineru_output" / "images"
    img_dst = paper_dir / "medias"
    if not full_md.exists():
        print(f"ERROR: {full_md} not found")
        sys.exit(1)
    text = full_md.read_text(encoding="utf-8")
    refs = set(re.findall(r'images/([^)]+)', text))
    print(f"Found {len(refs)} references in full.md")
    img_dst.mkdir(exist_ok=True)
    copied = 0
    for fname in sorted(refs):
        src = img_src / fname
        if src.exists():
            shutil.copy2(src, img_dst / fname)
            copied += 1
        else:
            print(f"  [missing] {fname}")
    print(f"Copied {copied}/{len(refs)} to {img_dst}")

if __name__ == "__main__":
    main()
