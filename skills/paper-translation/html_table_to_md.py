#!/usr/bin/env python3
"""Convert HTML <table> blocks in a Markdown file to pipe-table syntax.

Usage: python html_table_to_md.py <file.md> [--in-place]
"""
import re, sys
from pathlib import Path

def html_to_md_table(html: str) -> str:
    """Convert a single HTML <table>...</table> to Markdown pipe table."""
    # Extract rows
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    md_rows = []
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        md_rows.append('| ' + ' | '.join(cells) + ' |')

    if not md_rows:
        return html  # can't parse, keep original

    # Add separator after header
    header = md_rows[0]
    ncols = header.count('|') - 1
    sep = '|' + '|'.join([' --- '] * ncols) + '|'
    md_rows.insert(1, sep)

    return '\n'.join(md_rows)


def main():
    if len(sys.argv) < 2:
        print("Usage: python html_table_to_md.py <file.md> [--in-place]")
        sys.exit(1)

    path = Path(sys.argv[1])
    text = path.read_text(encoding='utf-8')
    tables = list(re.finditer(r'<table>.*?</table>', text, re.DOTALL))
    print(f"Found {len(tables)} HTML table(s)")

    for t in reversed(tables):  # replace from end to preserve positions
        md = html_to_md_table(t.group())
        text = text[:t.start()] + md + text[t.end():]

    out_path = path if '--in-place' in sys.argv else path.with_suffix('.converted.md')
    out_path.write_text(text, encoding='utf-8')
    print(f"Saved: {out_path}")


if __name__ == '__main__':
    main()
