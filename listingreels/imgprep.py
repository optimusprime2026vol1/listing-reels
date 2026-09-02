"""Image preparation: fill a 9:16 canvas, subtle auto-enhance, draw captions."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def fit_to_canvas(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Cover-crop `img` to exactly fill `size` (no letterboxing)."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    target_w, target_h = size
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # source is wider than target -> crop left/right
        new_w = int(src_h * target_ratio)
        offset = (src_w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, src_h))
    else:
        # source is taller than target -> crop top/bottom
        new_h = int(src_w / target_ratio)
        offset = (src_h - new_h) // 3  # bias crop upward (keep ceilings/windows)
        img = img.crop((0, offset, src_w, offset + new_h))

    return img.resize(size, Image.LANCZOS)


def auto_enhance(img: Image.Image) -> Image.Image:
    """Subtle, realistic brightening/contrast/sharpening -- not an artificial look."""
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(1.08)
    img = ImageEnhance.Brightness(img).enhance(1.04)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    return img


def draw_caption(img: Image.Image, text: str) -> Image.Image:
    """Draw a room/feature caption with a soft gradient bar for legibility."""
    if not text:
        return img
    img = img.copy()
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_h = int(h * 0.16)
    for i in range(bar_h):
        alpha = int(160 * (i / bar_h))
        y = h - bar_h + i
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    font = _font(FONT_BOLD, int(w * 0.052))
    draw.text((w * 0.06, h - bar_h * 0.62), text, font=font, fill=(255, 255, 255, 255))

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def build_end_card(
    size: tuple[int, int], title: str, address: str, price: str, agent: str
) -> Image.Image:
    """Branded closing slide: title, address, price, agent line."""
    w, h = size
    img = Image.new("RGB", size, (17, 17, 20))
    draw = ImageDraw.Draw(img)

    title_font = _font(FONT_BOLD, int(w * 0.09))
    addr_font = _font(FONT_REG, int(w * 0.05))
    price_font = _font(FONT_BOLD, int(w * 0.075))
    agent_font = _font(FONT_REG, int(w * 0.04))

    cy = h * 0.38
    if title:
        _draw_centered(draw, title, title_font, w, cy, fill=(255, 255, 255))
        cy += int(w * 0.09) * 1.3
    if price:
        _draw_centered(draw, price, price_font, w, cy, fill=(255, 210, 120))
        cy += int(w * 0.075) * 1.4
    if address:
        _draw_centered(draw, address, addr_font, w, cy, fill=(220, 220, 220))
        cy += int(w * 0.05) * 1.6
    if agent:
        _draw_centered(draw, agent, agent_font, w, h * 0.9, fill=(160, 160, 160))

    return img


def _draw_centered(draw, text, font, canvas_w, y, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((canvas_w - tw) / 2, y), text, font=font, fill=fill)


def load_prepared_frame(
    path: Path, size: tuple[int, int], caption: str = ""
) -> Image.Image:
    """Full per-photo prep: load -> cover-crop -> enhance -> caption."""
    img = Image.open(path)
    img = fit_to_canvas(img, size)
    img = auto_enhance(img)
    img = draw_caption(img, caption)
    return img
