import re
import argparse
import argostranslate.translate as translate

# ---- Load the offline en->zh model ----
langs = translate.get_installed_languages()
en = [l for l in langs if l.code == "en"][0]
zh = [l for l in langs if l.code == "zh"][0]
TRANS = en.get_translation(zh)

_cache = {}

def translate_text(s):
    """Translate a piece of plain prose. Cached for repeated boilerplate."""
    if s is None or s == "":
        return s
    if s in _cache:
        return _cache[s]
    try:
        out = TRANS.translate(s)
    except Exception:
        out = s
    _cache[s] = out
    return out


# Single-group token pattern: inline code | image | link | html
TOKEN = re.compile(r"(`[^`]+`|!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)|<[^>]+>)")
INLINE_CODE = re.compile(r"^`[^`]+`$")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]*)\)$")
LINK = re.compile(r"^\[([^\]]*)\]\(([^)]*)\)$")
HTML = re.compile(r"^<[^>]+>$")


def translate_inline(text):
    """Translate prose while preserving inline code, links, images, html."""
    if text is None:
        return text
    parts = TOKEN.split(text)
    out = []
    for part in parts:
        if part is None:
            continue
        if INLINE_CODE.fullmatch(part):
            out.append(part)                       # keep code verbatim
        elif IMAGE.fullmatch(part):
            m = IMAGE.fullmatch(part)
            out.append("![" + translate_text(m.group(1)) + "](" + m.group(2) + ")")
        elif LINK.fullmatch(part):
            m = LINK.fullmatch(part)
            out.append("[" + translate_text(m.group(1)) + "](" + m.group(2) + ")")
        elif HTML.fullmatch(part):
            out.append(part)                       # keep html verbatim
        else:
            out.append(translate_text(part))
    return "".join(out)


HEADING = re.compile(r"^(#{1,6})(\s+)(.*)$")
QUOTE = re.compile(r"^(>{1,6})(\s?)(.*)$")
TABLE_SEP = re.compile(r"^[\|\-\:\s]+$")


def translate_line(line):
    if line.strip() == "":
        return line
    m = HEADING.match(line)
    if m:
        return m.group(1) + m.group(2) + translate_inline(m.group(3))
    m = QUOTE.match(line)
    if m:
        return m.group(1) + m.group(2) + translate_inline(m.group(3))
    # table row
    if "|" in line and not TABLE_SEP.fullmatch(line.strip()):
        cells = line.split("|")
        new_cells = []
        for c in cells:
            if c.strip() == "":
                new_cells.append(c)
            else:
                new_cells.append(translate_inline(c))
        return "|".join(new_cells)
    return translate_inline(line)


def translate_unit(unit):
    if not unit.strip():
        return unit
    lines = unit.split("\n")
    return "\n".join(translate_line(ln) for ln in lines)


def is_verbatim_line(line):
    s = line.strip()
    if s == "":
        return False
    if "|" in s and TABLE_SEP.fullmatch(s):       # table separator row
        return True
    if re.fullmatch(r"(-\s*){3,}", s):
        return True
    if re.fullmatch(r"(\*\s*){3,}", s):
        return True
    if re.fullmatch(r"(_\s*){3,}", s):
        return True
    if re.fullmatch(r"(=\s*){3,}", s):             # setext heading underline
        return True
    return False


def translate_markdown(text):
    lines = text.split("\n")
    out = []
    buf = []
    in_code = False
    code_buf = []

    def flush():
        nonlocal buf
        if buf:
            out.append(translate_unit("\n".join(buf)))
            buf = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        if not in_code and stripped.startswith("```"):
            flush()
            in_code = True
            code_buf = [line]
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            if stripped.startswith("```") and len(code_buf) > 1:
                in_code = False
                out.append("\n".join(code_buf))
                code_buf = []
            i += 1
            continue
        if is_verbatim_line(line):
            flush()
            out.append(line)
            i += 1
            continue
        if line.strip() == "":
            flush()
            out.append("")
            i += 1
            continue
        buf.append(line)
        i += 1
    flush()
    if code_buf:
        out.append("\n".join(code_buf))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args()
    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()
    result = translate_markdown(text)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Translated {len(text)} chars -> {len(result)} chars")


if __name__ == "__main__":
    main()