import os, re, sys, zipfile #, collections

from ebooklib import epub #, ITEM_DOCUMENT
from markdownify import MarkdownConverter

IMG_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')

EPUB = sys.argv[1] if len(sys.argv) > 1 else r"E:/eBooks/AI  ML - Frontiers in Cross Disciplinary Applications/AI  ML - Frontiers in Cross Disciplinary Applications.epub"

def safe(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

STEM = safe(os.path.splitext(os.path.basename(EPUB))[0])
# OUTDIR = os.path.join(os.path.dirname(EPUB), STEM + "_markdown")
OUTDIR = os.path.dirname(EPUB)
IMG_DIR = os.path.join(OUTDIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

zf = zipfile.ZipFile(EPUB)
zip_names = zf.namelist()

# Path-agnostic image map: basename -> full zip path (unique basenames assumed)
img_map = {}
for n in zip_names:
    if n.lower().endswith(IMG_EXT):
        img_map[os.path.basename(n)] = n

def extract_image(basename):
    if basename in img_map:
        dest = os.path.join(IMG_DIR, basename)
        if not os.path.exists(dest):
            with open(dest, 'wb') as f:
                f.write(zf.read(img_map[basename]))
        return 'images/' + basename
    return None

class EpubConverter(MarkdownConverter):
    # Tags that introduce a block-level (line-breaking) context in Markdown.
    # Anything not in this set is treated as inline; a literal newline between
    # two inline siblings must collapse to a single space.
    _BLOCK_TAGS = {
        'address', 'article', 'aside', 'audio', 'blockquote', 'canvas', 'dd',
        'div', 'dl', 'dt', 'fieldset', 'figcaption', 'figure', 'footer',
        'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup',
        'hr', 'iframe', 'li', 'main', 'nav', 'noscript', 'ol', 'output',
        'p', 'pre', 'section', 'table', 'tbody', 'td', 'tfoot', 'th',
        'thead', 'tr', 'ul', 'video', 'body', 'script', 'style', 'html',
        'caption',
    }

    def _is_inline(self, node):
        if node is None:
            return False
        name = getattr(node, 'name', None)
        if name is None:
            return True  # a text node is inline
        return name not in self._BLOCK_TAGS

    def convert_span(self, el, text, **kwargs):
        # <span> is purely inline; by default markdownify leaves the
        # children's text verbatim, and process_text() normalizes any
        # internal whitespace/newlines into literal '\n' characters. That
        # splits a wrapped phrase across lines in the Markdown output, so
        # collapse every internal line break back into a single space.
        if not text:
            return ''
        return re.sub(r'[ \t\r\n]*\n[ \t\r\n]*', ' ', text)

    def process_text(self, el, parent_tags=None):
        text = super().process_text(el, parent_tags=parent_tags)
        # The common EPUB pattern <span>...</span>\n<span>...</span> places a
        # whitespace-only text node (a single '\n') between two inline
        # siblings. markdownify would otherwise emit that '\n' as a hard line
        # break. Collapse it to one space so spans flow inline. Never touch
        # preformatted/code contexts, where whitespace is significant.
        if (text and '\n' in text and text.strip() == ''
                and parent_tags is not None
                and 'pre' not in parent_tags and '_noformat' not in parent_tags):
            prev = getattr(el, 'previous_sibling', None)
            nxt = getattr(el, 'next_sibling', None)
            if self._is_inline(prev) and self._is_inline(nxt):
                text = ' '
        return text

# Pre-extract every image referenced anywhere in the book (preserves all pictures)
for b in img_map:
    extract_image(b)


def html_to_md(html_bytes):
    html = html_bytes.decode('utf-8', errors='replace')
    html = re.sub(r'<\?xml.*?\?>', '', html, flags=re.S)
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.S)
    return EpubConverter(strip=['style', 'script'], heading_style='ATX').convert(html)

book = epub.read_epub(EPUB)

def meta(ns, name):
    vals = book.get_metadata(ns, name)
    return vals[0][0] if vals else ''

title =  STEM
creator = meta('DC', 'creator') or ''
language = meta('DC', 'language') or ''

# Cover detection
cover_rel = None
cover_basenames = [b for b in img_map if re.search(r'cover', b, re.I)]
if cover_basenames:
    cb = sorted(cover_basenames, key=lambda x: len(x))[0]  # prefer shortest / most likely the real cover
    cover_rel = extract_image(cb)

# Reading order from spine.
# NOTE: some EPUBs declare chapter media-type as text/html but ebooklib
# misclassifies them as ITEM_UNKNOWN (type 0), so we select documents by
# file extension instead of ebooklib type. We skip the navigation/TOC doc
# and the cover (cover is handled separately), and dedupe by name.
manifest = {item.id: item for item in book.get_items()}
docs = []
seen = set()
for sid in book.spine:
    idref = sid[0] if isinstance(sid, tuple) else sid
    item = manifest.get(idref)
    if item is None:
        continue
    nm = item.get_name().lower()
    if not nm.endswith(('.html', '.xhtml')):
        continue
    if 'nav' in nm:                       # skip table-of-contents / navigation doc
        continue
    if nm.endswith(('cover.xhtml', 'cover.html')):  # cover handled separately
        continue
    if nm in seen:                        # skip duplicate spine entries (e.g. welcome.html twice)
        continue
    seen.add(nm)
    docs.append(item)

parts = []
if cover_rel:
    parts.append('![Cover](%s)\n' % cover_rel)
parts.append('# %s\n' % title)
if creator:
    parts.append('\n*by %s*\n' % creator)
if language:
    parts.append('\nLanguage: %s\n' % language)
parts.append('\n')

for item in docs:
    # print("原始:",item.get_content())
    md = html_to_md(item.get_content())
    # print("转换：",md)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    if md:
        parts.append(md + '\n\n')

final = '\n'.join(parts)
# remove any residual XML declarations (full PI form and bare lines) from SVG/embedded content
final = re.sub(r'<\?xml.*?\?>', '', final, flags=re.S)
final = re.sub(r'(?m)^\s*xml version=.*?\?\s*$', '', final)
final = re.sub(r'\n{3,}', '\n\n', final).strip() + '\n'

out_md = os.path.join(OUTDIR, safe(title) + '.md')
with open(out_md, 'w', encoding='utf-8') as f:
    f.write(final)

n_images = len(os.listdir(IMG_DIR))
print('Converted %d documents' % len(docs))
print('Output markdown:', out_md)
print('Images extracted:', n_images)
print('Markdown size (bytes):', os.path.getsize(out_md))