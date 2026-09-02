"""Turn a single still frame into a short Ken Burns (pan/zoom) video clip."""
from __future__ import annotations

import itertools

from moviepy import CompositeVideoClip, ImageClip
from PIL import Image

MAX_ZOOM = 1.14
EFFECTS = ("zoom-in", "zoom-out", "pan-left", "pan-right")


def _effect_cycle():
    return itertools.cycle(EFFECTS)


def ken_burns_clip(frame: Image.Image, duration: float, size: tuple[int, int], effect: str):
    """Build a moving CompositeVideoClip from a still PIL frame already sized to `size`."""
    import numpy as np

    w, h = size
    base = ImageClip(np.array(frame)).with_duration(duration)

    if effect == "zoom-in":
        z0, z1 = 1.0, MAX_ZOOM
        pos = _center_pos(w, h, lambda t: z0 + (z1 - z0) * (t / duration))
    elif effect == "zoom-out":
        z0, z1 = MAX_ZOOM, 1.0
        pos = _center_pos(w, h, lambda t: z0 + (z1 - z0) * (t / duration))
    elif effect in ("pan-left", "pan-right"):
        z0 = z1 = MAX_ZOOM
        direction = "right" if effect == "pan-right" else "left"
        pos = _pan_pos(w, h, MAX_ZOOM, duration, direction)
    else:
        z0 = z1 = 1.0
        pos = ("center", "center")

    clip = base.resized(lambda t: z0 + (z1 - z0) * (t / duration))
    clip = clip.with_position(pos)
    return CompositeVideoClip([clip], size=size).with_duration(duration)


def _center_pos(w, h, zoom_func):
    def f(t):
        z = zoom_func(t)
        return (-w * (z - 1) / 2, -h * (z - 1) / 2)

    return f


def _pan_pos(w, h, zoom, duration, direction):
    extra_x = w * (zoom - 1)
    y_offset = -h * (zoom - 1) / 2

    def f(t):
        frac = min(max(t / duration, 0), 1)
        if direction == "right":
            x_offset = -extra_x * frac
        else:
            x_offset = -extra_x * (1 - frac)
        return (x_offset, y_offset)

    return f
