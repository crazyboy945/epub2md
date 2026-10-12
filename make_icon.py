"""Generate e2m.ico — a Windows executable icon for e2m.py (epub -> markdown).

Design: a rounded blue gradient tile holding an open book (EPUB) with a
bold "M" (Markdown) centered on the pages. Rendered at 4x for anti-aliasing
and exported as a multi-size .ico (16..256).
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
S = 1024  # supersample render size

# ---- palette ----
TILE_TOP = (79, 124, 255, 255)
TILE_BOT = (28, 60, 200, 255)
PAGE_L = (255, 255, 255, 255)
PAGE_R = (226, 233, 255, 255)
SPINE = (180, 195, 255, 255)
M_COLOR = (26, 54, 184, 255)
SHADOW = (8, 16, 48, 34)


def make_gradient(size, top, bottom):
    w, h = size
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        f = y / max(1, h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(4))
        d.line([(0, y), (w, y)], fill=c)
    return img


def rounded_mask(size, radius):
    w, h = size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return m


def build_icon():
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # --- tile with gradient + rounded corners ---
    grad = make_gradient((S, S), TILE_TOP, TILE_BOT)
    mask = rounded_mask((S, S), int(S * 0.22))
    tile = Image.new("RGBA", (S, S))
    tile.paste(grad, (0, 0), mask)

    # subtle top-left highlight
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle(
        [int(S * 0.06), int(S * 0.04), int(S * 0.94), int(S * 0.48)],
        radius=int(S * 0.20), fill=(255, 255, 255, 26))
    tile = Image.alpha_composite(tile, hl)
    canvas = Image.alpha_composite(canvas, tile)

    d = ImageDraw.Draw(canvas)
    cx = S / 2
    hw = S * 0.35
    ty = S * 0.28
    by = S * 0.62
    ins = S * 0.05

    # soft blurred shadow to ground the book
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [cx - hw * 0.9, by - S * 0.01, cx + hw * 0.9, by + S * 0.11],
        fill=(8, 16, 48, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.028))
    canvas = Image.alpha_composite(canvas, shadow)
    d = ImageDraw.Draw(canvas)

    # open book: two pages meeting at a center spine
    left = [(cx - hw, ty + ins), (cx, ty), (cx, by), (cx - hw, by - ins)]
    right = [(cx + hw, ty + ins), (cx, ty), (cx, by), (cx + hw, by - ins)]
    d.polygon(left, fill=PAGE_L)
    d.polygon(right, fill=PAGE_R)
    d.line(left + [left[0]], fill=(206, 216, 255, 255), width=max(2, int(S * 0.005)))
    d.line(right + [right[0]], fill=(206, 216, 255, 255), width=max(2, int(S * 0.005)))
    d.line([(cx, ty), (cx, by)], fill=SPINE, width=max(2, int(S * 0.013)))

    # bold "M" (Markdown) centered on the book, kept inside the pages
    font_path = r"C:/Windows/Fonts/arialbd.ttf"
    fs = int(S * 0.40)
    font = ImageFont.truetype(font_path, fs)
    bbox = d.textbbox((0, 0), "M", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    mx = cx - tw / 2 - bbox[0]
    my = (ty + by) / 2 - th / 2 - bbox[1]
    d.text((mx, my), "M", font=font, fill=M_COLOR)

    return canvas


def main():
    master = build_icon().resize((256, 256), Image.LANCZOS)

    # multi-size .ico (downscaled from the 4x master for smoothness)
    ico_master = build_icon()
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico = Image.new("RGBA", (256, 256))
    ico.paste(ico_master.resize((256, 256), Image.LANCZOS))
    ico_path = os.path.join(HERE, "e2m.ico")
    ico.save(ico_path, format="ICO", sizes=sizes)

    # preview png
    preview_path = os.path.join(HERE, "e2m_icon_preview.png")
    build_icon().resize((1024, 1024), Image.LANCZOS).save(preview_path)

    print("wrote", ico_path, os.path.getsize(ico_path), "bytes")
    print("wrote", preview_path)
    print("ico sizes embedded:", sizes)


if __name__ == "__main__":
    main()
