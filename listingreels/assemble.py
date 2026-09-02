"""Orchestrate the full pipeline: photos -> Ken Burns clips -> crossfades -> audio -> mp4."""
from __future__ import annotations

from pathlib import Path

from moviepy import CompositeVideoClip, ImageClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn, CrossFadeOut

from .audio import build_audio_track
from .config import ListingConfig
from .imgprep import build_end_card, load_prepared_frame
from .motion import _effect_cycle, ken_burns_clip

END_CARD_DURATION = 3.2


def build_reel(cfg: ListingConfig, verbose: bool = True) -> str:
    size = cfg.resolution
    effects = _effect_cycle()

    clips = []
    for spec, path in zip(cfg.photos, cfg.photo_paths):
        if verbose:
            print(f"  preparing {path.name} ({spec.room or 'photo'})")
        frame = load_prepared_frame(path, size, caption=spec.caption or spec.room)
        effect = next(effects)
        clip = ken_burns_clip(frame, spec.duration, size, effect)
        clips.append(clip)

    # end card
    import numpy as np

    end_frame = build_end_card(size, cfg.title, cfg.address, cfg.price, cfg.agent)
    end_clip = ImageClip(np.array(end_frame)).with_duration(END_CARD_DURATION)
    end_clip = CompositeVideoClip([end_clip], size=size).with_duration(END_CARD_DURATION)
    clips.append(end_clip)

    # crossfade transitions
    t = cfg.transition
    faded = []
    for i, c in enumerate(clips):
        effects_list = []
        if i > 0:
            effects_list.append(CrossFadeIn(t))
        if i < len(clips) - 1:
            effects_list.append(CrossFadeOut(t))
        faded.append(c.with_effects(effects_list) if effects_list else c)

    final = concatenate_videoclips(faded, method="compose", padding=-t)

    audio = build_audio_track(
        duration=final.duration,
        music_path=cfg.music,
        music_volume=cfg.music_volume,
        voiceover_path=cfg.voiceover,
    )
    if audio is not None:
        final = final.with_audio(audio)

    out_path = Path(cfg.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"  rendering {out_path} ({final.duration:.1f}s @ {cfg.fps}fps)...")

    final.write_videofile(
        str(out_path),
        fps=cfg.fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar" if verbose else None,
    )
    return str(out_path)
