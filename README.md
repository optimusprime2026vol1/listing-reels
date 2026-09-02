# listing-reels

Turn a folder of real-estate interior photos into a finished vertical reel
(Instagram / TikTok / YouTube Shorts) — Ken Burns pan & zoom, room captions,
crossfades, background music, and a branded end card with price/address.

No paid APIs required to run. Pure Python + ffmpeg.

## What it does

For each listing you provide a small YAML config (photo order, room labels,
captions, price, address) and a folder of photos. The pipeline:

1. Cover-crops every photo to a clean 9:16 canvas
2. Applies a subtle, realistic auto-enhance (contrast/color/sharpen — not
   over-processed)
3. Animates each photo with a Ken Burns pan/zoom effect (cycles through
   zoom-in, zoom-out, pan-left, pan-right for variety)
4. Burns in a room caption on each clip
5. Crossfades between clips
6. Appends a branded end card (title, price, address, agent line)
7. Mixes in looped background music and/or a voiceover track
8. Exports a single `.mp4`

## Install

```bash
pip install -r requirements.txt
# ffmpeg must be on PATH (apt install ffmpeg / brew install ffmpeg)
```

## Try it with sample photos

```bash
python scripts/generate_sample_photos.py
python -m listingreels build --listing configs/123-main-st.yaml
# -> output/123-main-st.mp4
```

## Use it with your own listing

1. Put your photos in a folder, e.g. `assets/photos/my-listing/`
2. Copy `configs/123-main-st.yaml` to `configs/my-listing.yaml` and edit:

```yaml
title: "42 Ocean Ave"
address: "42 Ocean Ave, Newport"
price: "$1,250,000"
agent: "Listed by Jane Doe · Coastal Realty"

photos_dir: "assets/photos/my-listing"
photos:
  - file: 01-exterior.jpg
    room: "Welcome Home"
  - file: 02-living.jpg
    room: "Living Room"
    caption: "Vaulted ceilings, ocean views"
  - file: 03-kitchen.jpg
    room: "Chef's Kitchen"

music: "assets/music/upbeat.mp3"
music_volume: 0.5
voiceover: null

resolution: [1080, 1920]
fps: 30
transition: 0.4
output: "output/my-listing.mp4"
```

3. Run:

```bash
python -m listingreels build --listing configs/my-listing.yaml
```

## Project layout

```
listingreels/
  config.py    # YAML -> typed ListingConfig
  imgprep.py   # crop-to-fill, auto-enhance, captions, end card
  motion.py    # Ken Burns pan/zoom clip generator
  audio.py     # music looping + voiceover mixing
  assemble.py  # orchestrates the full build
  cli.py       # `listingreels build --listing ...`
scripts/
  generate_sample_photos.py
configs/
  123-main-st.yaml   # example config
```

## Build in the cloud (no local install)

A GitHub Actions workflow (`.github/workflows/build-reels.yml`) builds every
reel automatically -- you never need Python, ffmpeg, or this repo checked
out on your own machine.

1. **One-time setup**: in the repo, go to Settings → Actions → General →
   Workflow permissions, and select "Read and write permissions" (needed so
   the workflow can publish a release with your video).
2. Add your photos under `assets/photos/<listing-name>/` and a matching
   `configs/<listing-name>.yaml`, then commit and push (or upload the files
   directly in the GitHub web UI -- no git CLI needed).
3. Push to `main`. The Actions tab will show a running build.
4. When it finishes, check the repo's **Releases** page -- your `.mp4` is
   attached there, ready to download and post. It's also uploaded as a
   workflow run artifact.

Every push that touches `configs/`, `assets/photos/`, `assets/music/`, or
`assets/voiceover/` rebuilds *all* listing configs and publishes a new
release tagged `build-<run number>`.

## Notes / next steps

- **Voiceover**: `voiceover` in the config points to a pre-rendered audio
  file. Plug in any TTS service (or an AI voice tool) to generate that file
  from your listing description, then point the config at it.
- **Music**: any royalty-free / licensed mp3 works. It's looped or trimmed
  to match the final video length automatically.
- **Batch mode**: for now the CLI builds one listing at a time — wrap it in
  a shell loop or extend `cli.py` with a `build-all` command that globs
  `configs/*.yaml`.
