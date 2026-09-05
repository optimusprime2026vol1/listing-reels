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

    def build_body(params: dict) -> dict:
        return {
            "instances": [
                {
                    "prompt": prompt,
                    # Veo rejects `inlineData`/`fileUri` with a 400; the first-frame
                    # image must use `bytesBase64Encoded` + `mimeType`.
                    "image": {"bytesBase64Encoded": image_b64, "mimeType": mime_type},
                }
            ],
            "parameters": params,
        }

    def offending_param(error_text: str, params: dict) -> str | None:
        """If the API named a parameter in its error, return that key."""
        for key in params:
            if f"`{key}`" in error_text or f"'{key}'" in error_text or f'"{key}"' in error_text:
                return key
        return None

    # Start with the ideal settings. If the API rejects the request, drop the
    # exact parameter it named (or the next optional one) and retry, so a
    # single unsupported option can't fail the whole run.
    params = {
        "aspectRatio": "9:16",
        "resolution": "1080p",
        "durationSeconds": 8,
        "personGeneration": "allow_adult",
    }
    # Least important first -- these get dropped if the API doesn't say which.
    drop_order = ["personGeneration", "durationSeconds", "resolution", "aspectRatio"]

    op_name = None
    for attempt in range(1, 6):
        print(f"Submitting {args.image} to {model} (attempt {attempt}: {params})...")
        resp = requests.post(
            f"{BASE_URL}/models/{model}:predictLongRunning",
            headers=headers,
            json=build_body(params),
            timeout=120,
        )
        if resp.ok:
            op_name = resp.json().get("name")
            if op_name:
                break
            print(f"No operation name in response: {resp.text}")
            return 1

        print(f"Attempt {attempt} rejected ({resp.status_code}): {resp.text}")

        # Figure out what to change for the next attempt.
        bad = offending_param(resp.text, params)
        if bad == "resolution" and params.get("resolution") == "1080p":
            print("Retrying at 720p...")
            params = dict(params, resolution="720p")
            continue
        if bad:
            print(f"Dropping unsupported parameter: {bad}")
            params = {k: v for k, v in params.items() if k != bad}
            continue
        # API didn't name a parameter -- drop the least important remaining one.
        for key in drop_order:
            if key in params:
                print(f"Dropping '{key}' and retrying...")
                params = {k: v for k, v in params.items() if k != key}
                break
        else:
            print("No parameters left to adjust; giving up.")
            return 1
    else:
        print("All attempts failed.")
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
