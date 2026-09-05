"""Generate a photoreal AI walkthrough video from one reference photo using
Veo 3.1 through the Gemini API (simple API key auth -- no GCP service
account, no JSON key, no gcloud needed).

Docs: https://ai.google.dev/gemini-api/docs/veo

Requires env var:
  GEMINI_API_KEY  - from https://aistudio.google.com/apikey
Optional env var:
  VEO_MODEL_ID    - default "veo-3.1-generate-preview"
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time

import requests

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
POLL_INTERVAL_SECONDS = 15
MAX_WAIT_SECONDS = 20 * 60


def extract_video_uri(data: dict) -> str | None:
    try:
        return data["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
    except (KeyError, IndexError, TypeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("VEO_MODEL_ID", "veo-3.1-generate-preview")
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    with open(args.prompt_file, "r") as f:
        prompt = f.read().strip()

    mime_type, _ = mimetypes.guess_type(args.image)
    if mime_type not in ("image/jpeg", "image/png"):
        mime_type = "image/jpeg"

    with open(args.image, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    body = {
        "instances": [
            {
                "prompt": prompt,
                "image": {"inlineData": {"mimeType": mime_type, "data": image_b64}},
            }
        ],
        "parameters": {
            "aspectRatio": "9:16",
            "resolution": "1080p",
            # 1080p requires an 8s duration for image-to-video.
            "durationSeconds": "8",
            # Required value for image-to-video per Veo docs.
            "personGeneration": "allow_adult",
        },
    }

    print(f"Submitting {args.image} to {model}...")
    resp = requests.post(
        f"{BASE_URL}/models/{model}:predictLongRunning",
        headers=headers,
        json=body,
        timeout=120,
    )
    if not resp.ok:
        print(f"Submit failed ({resp.status_code}): {resp.text}")
        return 1
    op_name = resp.json().get("name")
    if not op_name:
        print(f"No operation name in response: {resp.text}")
        return 1
    print(f"Operation submitted: {op_name}")

    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        poll = requests.get(f"{BASE_URL}/{op_name}", headers=headers, timeout=60)
        if not poll.ok:
            print(f"Poll failed ({poll.status_code}): {poll.text}")
            return 1
        data = poll.json()
        if data.get("done"):
            if "error" in data:
                print("Generation failed:", json.dumps(data["error"], indent=2))
                return 1
            video_uri = extract_video_uri(data)
            if not video_uri:
                print("Could not find a video URI in the completed response.")
                print(json.dumps(data, indent=2)[:4000])
                return 1
            print(f"Downloading video from {video_uri}")
            dl = requests.get(video_uri, headers=headers, timeout=180, stream=True)
            if not dl.ok:
                print(f"Download failed ({dl.status_code}): {dl.text[:500]}")
                return 1
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            with open(args.out, "wb") as f:
                for chunk in dl.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
            print(f"Saved {args.out}")
            return 0
        print("Still rendering...")

    print("Timed out waiting for video generation.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
