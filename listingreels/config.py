"""Load and validate a listing config (YAML) into typed objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PhotoSpec:
    file: str
    room: str = ""
    caption: str = ""
    duration: float = 2.6  # seconds this photo stays on screen


@dataclass
class ListingConfig:
    title: str
    address: str
    price: str = ""
    agent: str = ""
    photos_dir: str = "."
    photos: list[PhotoSpec] = field(default_factory=list)
    music: Optional[str] = None
    music_volume: float = 0.5
    voiceover: Optional[str] = None  # path to a pre-rendered voiceover audio file
    resolution: tuple[int, int] = (1080, 1920)  # 9:16
    fps: int = 30
    transition: float = 0.4  # crossfade seconds between photos
    output: str = "output/reel.mp4"

    @property
    def photo_paths(self) -> list[Path]:
        base = Path(self.photos_dir)
        return [base / p.file for p in self.photos]


def load_config(path: str | Path) -> ListingConfig:
    path = Path(path)
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ValueError(f"Config file {path} is empty or invalid")

    photos_raw = raw.get("photos", [])
    photos = [
        PhotoSpec(
            file=p["file"],
            room=p.get("room", ""),
            caption=p.get("caption", ""),
            duration=float(p.get("duration", 2.6)),
        )
        for p in photos_raw
    ]

    if not photos:
        raise ValueError(f"Config {path} defines no photos")

    resolution = raw.get("resolution", [1080, 1920])

    # photos_dir defaults to a directory next to the config file if not set
    default_photos_dir = str(path.parent / "photos")
    photos_dir = raw.get("photos_dir", default_photos_dir)

    cfg = ListingConfig(
        title=raw["title"],
        address=raw.get("address", ""),
        price=raw.get("price", ""),
        agent=raw.get("agent", ""),
        photos_dir=photos_dir,
        photos=photos,
        music=raw.get("music"),
        music_volume=float(raw.get("music_volume", 0.5)),
        voiceover=raw.get("voiceover"),
        resolution=tuple(resolution),
        fps=int(raw.get("fps", 30)),
        transition=float(raw.get("transition", 0.4)),
        output=raw.get("output", "output/reel.mp4"),
    )

    missing = [p for p in cfg.photo_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing photo files: " + ", ".join(str(m) for m in missing)
        )

    return cfg
