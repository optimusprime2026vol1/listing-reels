"""Background music (looped/trimmed to length) mixed with an optional voiceover."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from moviepy import AudioFileClip, CompositeAudioClip
from moviepy.audio.fx import AudioLoop, MultiplyVolume


def build_audio_track(
    duration: float,
    music_path: Optional[str],
    music_volume: float = 0.5,
    voiceover_path: Optional[str] = None,
):
    """Return a moviepy AudioClip covering `duration` seconds, or None if no audio given."""
    tracks = []

    if music_path and Path(music_path).exists():
        music = AudioFileClip(music_path)
        if music.duration < duration:
            music = music.with_effects([AudioLoop(duration=duration)])
        else:
            music = music.subclipped(0, duration)
        music = music.with_effects([MultiplyVolume(music_volume)])
        tracks.append(music)

    if voiceover_path and Path(voiceover_path).exists():
        vo = AudioFileClip(voiceover_path)
        if vo.duration > duration:
            vo = vo.subclipped(0, duration)
        tracks.append(vo)

    if not tracks:
        return None
    if len(tracks) == 1:
        return tracks[0].with_duration(duration)
    return CompositeAudioClip(tracks).with_duration(duration)
