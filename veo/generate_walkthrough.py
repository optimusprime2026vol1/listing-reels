"""Generate a photoreal AI walkthrough video from one reference photo using
Veo on Vertex AI (image-to-video), via the predictLongRunning REST API.

Requires env vars:
  GCP_PROJECT_ID      - your Google Cloud project ID
  GOOGLE_ACCESS_TOKEN  - a bearer token (e.g. `gcloud auth print-access-token`)
Optional env vars:
  GCP_LOCATION        - default "us-central1"
  VEO_MODEL_ID        - default "veo-3.1-generate-001"
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

POLL_INTERVAL_SECONDS = 15
MAX_WAIT_SECONDS = 20 * 60


def build_request(prompt: str, image_bytes: bytes, mime_type: str) -> dict:
    return {
        "instances": [
            {
                "prompt": prompt,
                "image": {
                    "bytesBase64Encoded": base64.b64encode(image_bytes).decode("utf-8"),
                    "mimeType": mime_type,
                },
            }
        ],
        "parameters": {
            "aspectRatio": "9:16",
            "resolution": "1080p",
            # Google's API requires durationSeconds=8 for image-to-video at 1080p.
            "durationSeconds": 8,
            "sampleCount": 1,
        },
    }


def extract_video_b64(data: dict) -> str | None:
    """Defensively pull the base64 video out of a completed operation.

    Different doc snapshots for this API show the result under different
    keys (`predictions`, `videos`, `generatedSamples[].video`), so check all
    of them rather than assuming one shape.
    """
    response = data.get("response", {})
    for key in ("predictions", "videos"):
        items = response.get(key)
        if items:
            item = items[0]
            if isinstance(item, dict):
                if item.get("bytesBase64Encoded"):
                    return item["bytesBase64Encoded"]
                nested = item.get("video")
                if isinstance(nested, dict) and nested.get("bytesBase64Encoded"):
                    return nested["bytesBase64Encoded"]
    samples = response.get("generatedSamples")
    if samples:
        video = samples[0].get("video", {})
        if video.get("bytesBase64Encoded"):
            return video["bytesBase64Encoded"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    project = os.environ["GCP_PROJECT_ID"]
    location = os.environ.get("GCP_LOCATION", "us-central1")
    model = os.environ.get("VEO_MODEL_ID", "veo-3.1-generate-001")
    token = os.environ["GOOGLE_ACCESS_TOKEN"]

    with open(args.prompt_file, "r") as f:
        prompt = f.read().strip()

    mime_type, _ = mimetypes.guess_type(args.image)
    if mime_type not in ("image/jpeg", "image/png"):
        mime_type = "image/jpeg"

    with open(args.image, "rb") as f:
        image_bytes = f.read()

    base_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}"
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = build_request(prompt, image_bytes, mime_type)

    print(f"Submitting {args.image} to {model} in {location}...")
    resp = requests.post(f"{base_url}:predictLongRunning", headers=headers, json=body, timeout=120)
    if not resp.ok:
        print(f"Submit failed ({resp.status_code}): {resp.text}")
        return 1
    op_name = resp.json().get("name")
    if not op_name:
        print(f"No operation name in response: {resp.text}")
        return 1
    print(f"Operation submitted: {op_name}")

    poll_url = f"{base_url}:fetchPredictOperation"
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        poll = requests.post(poll_url, headers=headers, json={"operationName": op_name}, timeout=60)
        if not poll.ok:
            print(f"Poll failed ({poll.status_code}): {poll.text}")
            return 1
        data = poll.json()
        if data.get("done"):
            if "error" in data:
                print("Generation failed:", json.dumps(data["error"], indent=2))
                return 1
            video_b64 = extract_video_b64(data)
            if not video_b64:
                print("Could not find video bytes in the completed response.")
                print("Full response for debugging:")
                print(json.dumps(data, indent=2)[:4000])
                return 1
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            with open(args.out, "wb") as f:
                f.write(base64.b64decode(video_b64))
            print(f"Saved {args.out}")
            return 0
        print("Still rendering...")

    print("Timed out waiting for video generation.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
