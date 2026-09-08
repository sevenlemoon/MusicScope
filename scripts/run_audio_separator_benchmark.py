#!/usr/bin/env python3
"""Run the bounded Milestone 6A.5 demucs-infer benchmark.

The fixtures are deterministic, synthetic, and intentionally not a quality
study. This script measures runtime and verifies that two compatible WAV
outputs are produced.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import resource
import shutil
import struct
import subprocess
import tempfile
import time
import wave
from pathlib import Path


SAMPLE_RATE = 44_100


def write_music_like_fixture(path: Path, duration: float) -> None:
    frames = int(duration * SAMPLE_RATE)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for index in range(frames):
            seconds = index / SAMPLE_RATE
            beat = int(seconds * 2)  # 120 BPM
            kick = 0.28 * math.exp(-28 * (seconds - beat / 2) % 0.5)
            bass = 0.18 * math.sin(2 * math.pi * (110 if beat % 4 < 2 else 146.83) * seconds)
            vocal = 0.22 * math.sin(2 * math.pi * (440 + 18 * math.sin(seconds)) * seconds)
            pad = 0.09 * math.sin(2 * math.pi * 220 * seconds)
            sample = max(-1.0, min(1.0, kick + bass + vocal + pad))
            packed = struct.pack("<h", int(sample * 32767))
            output.writeframesraw(packed + packed)


def probe_audio(path: Path) -> dict[str, object]:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=sample_rate,channels,codec_name",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(probe.stdout)
    stream = data["streams"][0]
    return {
        "duration_seconds": float(data["format"]["duration"]),
        "sample_rate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "codec": stream["codec_name"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=os.environ.get("AUDIO_PYTHON", ".audio-venv312/bin/python"))
    parser.add_argument("--durations", nargs="+", type=float, default=[10.0, 30.0])
    parser.add_argument("--device", default="mps")
    args = parser.parse_args()

    # Do not resolve the venv's Python symlink before locating its scripts.
    # Homebrew Python resolves outside the venv, while the console script does
    # live beside the venv interpreter.
    separator = Path(args.python).absolute().parent / "demucs-infer"
    if not separator.exists():
        raise SystemExit(f"separator executable not found: {separator}")
    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe is required")

    results = []
    with tempfile.TemporaryDirectory(prefix="musicscope-demucs-benchmark-") as temp_dir:
        root = Path(temp_dir)
        for duration in args.durations:
            fixture = root / f"fixture-{int(duration)}s.wav"
            output_dir = root / f"output-{int(duration)}s"
            write_music_like_fixture(fixture, duration)
            command = [
                str(separator),
                "-n",
                "htdemucs",
                "-d",
                args.device,
                "-o",
                str(output_dir),
                "--two-stems",
                "vocals",
                "--other-method",
                "add",
                "--shifts",
                "1",
                "--segment",
                "7",
                str(fixture),
            ]
            started = time.perf_counter()
            process = subprocess.run(command, capture_output=True, text=True)
            elapsed = time.perf_counter() - started
            if process.returncode:
                raise SystemExit(process.stderr or process.stdout)

            vocals = next(output_dir.rglob("vocals.wav"))
            instrumental = next(output_dir.rglob("no_vocals.wav"))
            vocals_info = probe_audio(vocals)
            instrumental_info = probe_audio(instrumental)
            results.append(
                {
                    "duration_seconds": duration,
                    "processing_seconds": round(elapsed, 3),
                    "rtf": round(elapsed / duration, 4),
                    "device": args.device,
                    "outputs": {
                        "vocals": vocals_info,
                        "instrumental_from_no_vocals": instrumental_info,
                        "compatible": vocals_info == instrumental_info,
                    },
                    "command": command,
                }
            )

    print(
        json.dumps(
            {
                "machine": platform.machine(),
                "macos": platform.mac_ver()[0],
                "results": results,
                "peak_child_memory_mb": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024 / 1024, 1),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
