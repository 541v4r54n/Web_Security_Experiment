from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def add_text_watermark(src: Path, dst: Path, text: str) -> None:
    text = (text or "").strip()
    if not text:
        text = "WATERMARK"

    with Image.open(src) as im:
        base = im.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        margin = max(10, int(min(base.size) * 0.02))
        box = draw.textbbox((0, 0), text, font=font)
        text_w = box[2] - box[0]
        text_h = box[3] - box[1]
        x = base.size[0] - text_w - margin
        y = base.size[1] - text_h - margin

        # semi-transparent black background + white text
        pad = 6
        draw.rectangle([x - pad, y - pad, x + text_w + pad, y + text_h + pad], fill=(0, 0, 0, 110))
        draw.text((x, y), text, fill=(255, 255, 255, 230), font=font)

        out = Image.alpha_composite(base, overlay).convert("RGB")
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(dst, quality=92)

