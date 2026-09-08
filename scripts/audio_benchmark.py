#!/usr/bin/env python3
"""Dependency-free validation probe for the Milestone 6A audio benchmark.

This deliberately does not download models or run a separator. It creates a
small project-owned WAV fixture and reports whether the local prerequisites for
the real benchmark are available.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import platform
import shutil
import struct
import sys
import tempfile
import wave
from pathlib import Path


def write_fixture(path: Path, duration: float, sample_rate: int = 44_100) -> None:
    frames = int(duration * sample_rate)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            vocal = 0.35 * math.sin(2 * math.pi * 440 * time)
            instrumental = 0.25 * math.sin(2 * math.pi * 110 * time)
            sample = max(-1.0, min(1.0, vocal + instrumental))
            packed = struct.pack("<h", int(sample * 32767))
            output.writeframesraw(packed + packed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="musicscope-audio-benchmark-") as temp_dir:
        fixture = Path(temp_dir) / "synthetic-mix.wav"
        write_fixture(fixture, args.duration)
        report = {
            "status": "ready-for-engine-benchmark",
            "fixture": {"path": str(fixture), "duration_seconds": args.duration},
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "tools": {"ffmpeg": shutil.which("ffmpeg"), "afconvert": shutil.which("afconvert")},
            "python_packages": {
                name: importlib.util.find_spec(name) is not None
                for name in ("torch", "torchaudio", "demucs", "spleeter", "onnxruntime")
            },
            "separator_run": "skipped: no local separator dependencies/models were detected",
        }
        if report["tools"]["ffmpeg"] is None and not report["python_packages"]["torch"]:
            report["status"] = "blocked-missing-separator-runtime"
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
