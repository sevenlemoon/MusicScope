#!/usr/bin/env python3
"""Run one real local upload -> separation -> manifest smoke test."""

from __future__ import annotations

import io
import time
import wave

from fastapi.testclient import TestClient

from app.main import app


def main() -> int:
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 8000)

    client = TestClient(app)
    upload = client.post("/api/v1/audio-assets", files={"file": ("smoke.wav", audio.getvalue(), "audio/wav")})
    upload.raise_for_status()
    asset_id = upload.json()["id"]
    try:
        start = client.post(f"/api/v1/audio-assets/{asset_id}/separate")
        start.raise_for_status()
        job_id = start.json()["id"]
        for _ in range(120):
            job = client.get(f"/api/v1/separation-jobs/{job_id}").json()
            if job["status"] in {"COMPLETED", "FAILED"}:
                break
            time.sleep(1)
        if job["status"] != "COMPLETED":
            raise SystemExit(f"separation failed: {job}")
        manifest = client.get(f"/api/v1/separation-jobs/{job_id}/manifest")
        manifest.raise_for_status()
        for stem in ("vocals", "instrumental"):
            artifact = client.get(f"/api/v1/separation-jobs/{job_id}/artifacts/{stem}")
            artifact.raise_for_status()
            if not artifact.content:
                raise SystemExit(f"empty {stem} artifact")
        print({"job_id": job_id, "status": job["status"], "manifest": manifest.json()})
    finally:
        client.delete(f"/api/v1/audio-assets/{asset_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
