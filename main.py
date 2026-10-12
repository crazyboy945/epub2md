import os, re, zipfile

from ebooklib import epub, ITEM_DOCUMENT
from markdownify import MarkdownConverter
import click




IMG_RE = re.compile(r'(?:images/|\.\./images/)([^/]+\.(?:jpe?g|gif|png|svg|webp))', re.I)

# def ensure_image(src,zip_names,IMG_DIR):
#     """Extract an image referenced by src into IMG_DIR; return relative md path or None."""
#     m = IMG_RE.search(src or '')
#     if not m:
#         return None
#     fname = m.group(1)
#     zpath = 'images/' + fname
#     if zpath not in zip_names:
#         # try root-level (e.g. cover.jpeg)
#         if fname in zip_names:
#             zpath = fname
#         else:
#             return None
#     dest = os.path.join(IMG_DIR, fname)
#     if not os.path.exists(dest):
#         with open(dest, 'wb') as f:
#             f.write(zf.read(zpath))
#     return 'images/' + fname

class BookConverter(MarkdownConverter):
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

    def convert_a(self, el, text, **kwargs):
        href = (el.get('href') or '').strip()
        if href and (href.startswith('http://') or href.startswith('https://')
                     or href.startswith('mailto:') or href.startswith('//')):
            return super().convert_a(el, text, **kwargs)
        # strip internal .html cross-references to plain text
        return text or ''

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

    # def convert_img(self, el, text, zip_names,IMG_DIR,**kwargs):
    #     alt = el.get('alt', '') or ''
    #     src = el.get('src', '') or ''
    #     rel = ensure_image(src,zip_names,IMG_DIR)
    #     if rel:
    #         title = el.get('title', '')
    #         title_part = ' "%s"' % title if title else ''
    #         return '![%s](%s%s)' % (alt, rel, title_part)
    #     return super().convert_img(el, text, **kwargs)

def html_to_md(html_bytes):
    html = html_bytes.decode('utf-8', errors='replace')
    # strip XML declarations / processing instructions (kept as literal text by the parser)
    html = re.sub(r'<\?xml.*?\?>', '', html, flags=re.S)
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.S)
    return BookConverter(strip=['style', 'script'], heading_style='ATX').convert(html)



# ---- metadata ----
def meta(ns, book,name):
    vals = book.get_metadata(ns, name)
    if vals:
        return vals[0][0]
    return ''




@click.command()
@click.option("-p", "--path",type=str,help="需要转换epub文件路径")
def main(path):
    if os.path.exists(path):
        OUTDIR = os.path.dirname(path)
        print(OUTDIR)
        IMG_DIR = os.path.join(OUTDIR, "images")
        os.makedirs(IMG_DIR, exist_ok=True)
        # zf = zipfile.ZipFile(in_book)
        # zip_names = set(zf.namelist())


        book = epub.read_epub(path)

        title = meta('DC',book, 'title') or 'Book'
        creator = meta('DC',book,  'creator') or ''
        language = meta('DC',book,  'language') or ''

        # # ---- cover image ----
        # cover_rel = None
        # if 'cover.jpeg' in zip_names:
        #     with open(os.path.join(IMG_DIR, 'cover.jpeg'), 'wb') as f:
        #         f.write(zf.read('cover.jpeg'))
        #     cover_rel = 'images/cover.jpeg'

        # ---- build reading-order document list ----
        manifest = {item.id: item for item in book.get_items()}
        docs = []
        for sid in book.spine:
            idref = sid[0] if isinstance(sid, tuple) else sid
            item = manifest.get(idref)
            if item is not None and item.get_type() == ITEM_DOCUMENT:
                docs.append(item)

        # ---- convert ----
        parts = []
        # if cover_rel:
        #     parts.append('![Cover](%s)\n' % cover_rel)
        parts.append('# %s\n' % title)
        if creator:
            parts.append('\n*by %s*\n' % creator)
        if language:
            parts.append('\nLanguage: %s\n' % language)
        parts.append('\n')

        for item in docs:
            md = html_to_md(item.get_content())
            md = re.sub(r'\n{3,}', '\n\n', md).strip()
            if md:
                parts.append(md + '\n\n')

        final = '\n'.join(parts)
        final = re.sub(r'(?m)^xml version=.*?\?\s*$', '', final)
        final = re.sub(r'\n{3,}', '\n\n', final).strip() + '\n'

        out_md = os.path.join(OUTDIR, re.sub(r'[\\/:*?"<>|]', '', title).strip() + '.md')
        with open(out_md, 'w', encoding='utf-8') as f:
            f.write(final)

        n_images = len([n for n in os.listdir(IMG_DIR)])
        print('Converted', len(docs), 'documents')
        print('Output markdown:', out_md)
        print('Images extracted:', n_images)
        print('Markdown size (bytes):', os.path.getsize(out_md))

    else:
        print("输入的路径不正确.")



if __name__=='__main__':
    main()