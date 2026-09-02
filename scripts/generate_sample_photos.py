"""Generate placeholder room photos so you can test the pipeline without real listing photos."""
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOMS = [
    ("living-room.jpg", (235, 220, 200)),
    ("kitchen.jpg", (210, 225, 235)),
    ("bedroom.jpg", (225, 210, 225)),
    ("bathroom.jpg", (200, 230, 225)),
]


def main(out_dir: str = "assets/photos/123-main-st", seed: int = 0):
    random.seed(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, color in ROOMS:
        img = Image.new("RGB", (1600, 1067), color)
        d = ImageDraw.Draw(img)
        for _ in range(40):
            x0, y0 = random.randint(0, 1600), random.randint(0, 1067)
            x1, y1 = x0 + random.randint(20, 200), y0 + random.randint(20, 200)
            shade = tuple(max(0, c - random.randint(0, 40)) for c in color)
            d.rectangle([x0, y0, x1, y1], outline=shade, width=3)
        img.save(out / name)
        print(f"wrote {out / name}")


if __name__ == "__main__":
    main()
