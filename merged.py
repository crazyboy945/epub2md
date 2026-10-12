import os
import re
import sys
import click

SRC_DIR = r"F:\eBooks\Automate the Boring Stuff with Python, 3rd Edition"
OUT = os.path.join(SRC_DIR, "Automate the Boring Stuff with Python 3rd Edition - merged.md")

def sort_key(name):
    base = name
    if base.startswith("前言"):
        return (0, 0, base)
    m = re.match(r"第(\d+)章", base)
    if m:
        return (1, int(m.group(1)), base)
    m = re.match(r"附录([A-Za-z])", base)
    if m:
        return (2, ord(m.group(1).upper()) - ord("A") + 1, base)
    return (3, 0, base)  # others last


def main(path,option=".md"):
    files = [f for f in os.listdir(SRC_DIR) if f.lower().endswith(".md")]
    files.sort(key=sort_key)

    print("Merge order:")
    for f in files:
        print("  ", sort_key(f)[0], sort_key(f)[1], f)

    parts = []
    for f in files:
        path = os.path.join(SRC_DIR, f)
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if not text.endswith("\n"):
            text += "\n"
        # parts.append("<!-- 源文件: " + f + " -->\n" + text)

    merged = "\n\n".join(parts)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(merged)

    print(f"\nMerged {len(files)} files -> {OUT}")
    print(f"Total chars: {len(merged)}")