"""Local audio storage, normalization, and the small separation worker."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from .config import get_settings
from .db import SessionLocal
from .models import AudioAsset, SeparationJob, StemArtifact

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}
STEM_NAMES = ("vocals", "instrumental")
NORMALIZATION_CONFIG = {
    "format": "wav",
    "codec": "pcm_s16le",
    "sample_rate": 44100,
    "channels": 2,
}
SEPARATOR_ARGS = {"two_stems": "vocals", "other_method": "add", "shifts": 1, "segment": 7}
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="musicscope-separation")


class AudioProcessingError(RuntimeError):
    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or message


def storage_root() -> Path:
    root = Path(get_settings().audio_storage_dir)
    if not root.is_absolute():
        root = project_root() / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "apps" / "api").is_dir():
            return parent
    return Path.cwd()


def storage_key(path: Path) -> str:
    return path.resolve().relative_to(storage_root()).as_posix()


def storage_path(key: str) -> Path:
    root = storage_root()
    path = (root / key).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AudioProcessingError("Invalid audio artifact reference") from exc
    return path


def safe_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise AudioProcessingError("Unsupported audio format")
    return extension


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_audio(path: Path) -> dict[str, object]:
    if not path.exists() or path.stat().st_size == 0:
        raise AudioProcessingError("Audio file is empty or missing")
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,sample_rate,channels",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        payload = json.loads(result.stdout)
    except FileNotFoundError as exc:
        raise AudioProcessingError("FFprobe is required for audio validation") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise AudioProcessingError("The uploaded file is not readable audio", detail) from exc
    streams = [stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"]
    if not streams:
        raise AudioProcessingError("The uploaded file contains no audio stream")
    stream = streams[0]
    try:
        duration = float(payload["format"]["duration"])
        sample_rate = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AudioProcessingError("Audio metadata is incomplete") from exc
    if duration <= 0 or sample_rate <= 0 or channels <= 0:
        raise AudioProcessingError("Audio metadata is invalid")
    return {
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "codec": stream.get("codec_name"),
    }


def normalize_audio(source: Path, target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                str(NORMALIZATION_CONFIG["channels"]),
                "-ar",
                str(NORMALIZATION_CONFIG["sample_rate"]),
                "-c:a",
                str(NORMALIZATION_CONFIG["codec"]),
                str(target),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError as exc:
        raise AudioProcessingError("FFmpeg is required for audio normalization") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise AudioProcessingError("Audio normalization failed", detail) from exc
    return probe_audio(target)


def write_upload(stream: BinaryIO, target: Path, max_bytes: int) -> int:
    total = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise AudioProcessingError("Audio upload exceeds the 250 MB limit")
            output.write(chunk)
    return total


def store_uploaded_audio(stream: BinaryIO, filename: str, content_type: str | None, user_id: UUID) -> AudioAsset:
    settings = get_settings()
    extension = safe_extension(filename)
    asset_id = uuid4()
    root = storage_root()
    asset_dir = root / str(user_id) / str(asset_id)
    temp_dir = root / ".tmp" / str(uuid4())
    source_temp = temp_dir / f"source{extension}"
    normalized_temp = temp_dir / "normalized.wav"
    try:
        size = write_upload(stream, source_temp, settings.audio_max_upload_bytes)
        source_metadata = probe_audio(source_temp)
        if float(source_metadata["duration_seconds"]) > settings.audio_max_duration_seconds:
            raise AudioProcessingError("Audio duration exceeds the 15 minute limit")
        normalized_metadata = normalize_audio(source_temp, normalized_temp)
        asset_dir.mkdir(parents=True, exist_ok=True)
        source_path = asset_dir / f"source_original{extension}"
        normalized_path = asset_dir / "normalized.wav"
        os.replace(source_temp, source_path)
        os.replace(normalized_temp, normalized_path)
        asset = AudioAsset(
            id=asset_id,
            user_id=user_id,
            original_filename=filename[:255],
            source_storage_key=storage_key(source_path),
            normalized_storage_key=storage_key(normalized_path),
            source_sha256=sha256_file(source_path),
            source_size_bytes=size,
            source_content_type=content_type,
            source_codec=str(source_metadata.get("codec") or "unknown"),
            duration_seconds=float(normalized_metadata["duration_seconds"]),
            sample_rate=int(normalized_metadata["sample_rate"]),
            channels=int(normalized_metadata["channels"]),
        )
        db = SessionLocal()
        try:
            db.add(asset)
            db.commit()
            db.refresh(asset)
            return asset
        finally:
            db.close()
    except Exception:
        shutil.rmtree(asset_dir, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def separation_configuration() -> dict[str, object]:
    settings = get_settings()
    return {
        "normalization": NORMALIZATION_CONFIG,
        "separator": settings.separator_package,
        "separator_version": settings.separator_package_version,
        "model": settings.separator_model,
        "checkpoint": settings.separator_checkpoint,
        "device_preference": settings.separator_device,
        "args": SEPARATOR_ARGS,
        "output": {"format": "wav", "codec": "pcm_s16le"},
    }


def separation_fingerprint(asset: AudioAsset) -> str:
    payload = {"source_sha256": asset.source_sha256, **separation_configuration()}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def runtime_paths() -> tuple[Path, Path]:
    settings = get_settings()
    python_path = Path(settings.separator_python)
    executable = Path(settings.separator_executable)
    root = project_root()
    if not python_path.is_absolute():
        python_path = root / python_path
    if not executable.is_absolute():
        executable = root / executable
    if not python_path.exists() or not executable.exists():
        raise AudioProcessingError("The isolated audio separator runtime is not installed")
    return python_path, executable


def select_device(python_path: Path) -> str:
    settings = get_settings()
    if settings.separator_device == "cpu":
        return "cpu"
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import torch; print('mps' if torch.backends.mps.is_available() else 'cpu')"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        detected = result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AudioProcessingError("The isolated separator runtime cannot be validated", str(exc)) from exc
    if settings.separator_device == "mps" and detected != "mps":
        return "cpu"
    return detected if detected in {"mps", "cpu"} else "cpu"


def run_separator(input_path: Path, output_dir: Path, device: str) -> tuple[Path, Path]:
    python_path, executable = runtime_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                str(executable),
                "-n",
                get_settings().separator_model,
                "-d",
                device,
                "--two-stems",
                "vocals",
                "--other-method",
                "add",
                "--shifts",
                str(SEPARATOR_ARGS["shifts"]),
                "--segment",
                str(SEPARATOR_ARGS["segment"]),
                "-o",
                str(output_dir),
                str(input_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except FileNotFoundError as exc:
        raise AudioProcessingError("The isolated audio separator runtime is not installed") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioProcessingError("Audio separation timed out") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "separator failed")[-4000:]
        raise AudioProcessingError("Audio separation failed", detail) from exc
    try:
        return next(output_dir.rglob("vocals.wav")), next(output_dir.rglob("no_vocals.wav"))
    except StopIteration as exc:
        raise AudioProcessingError("Separator did not produce both expected stems") from exc


def validate_stems(vocals: Path, instrumental: Path, expected_duration: float) -> tuple[dict[str, object], dict[str, object]]:
    vocal_metadata = probe_audio(vocals)
    instrumental_metadata = probe_audio(instrumental)
    if vocal_metadata["sample_rate"] != instrumental_metadata["sample_rate"] or vocal_metadata["channels"] != instrumental_metadata["channels"]:
        raise AudioProcessingError("Separated stems have incompatible sample properties")
    if abs(float(vocal_metadata["duration_seconds"]) - float(instrumental_metadata["duration_seconds"])) > 0.05:
        raise AudioProcessingError("Separated stems have incompatible durations")
    if abs(float(vocal_metadata["duration_seconds"]) - expected_duration) > 0.1:
        raise AudioProcessingError("Separated stems do not match the source duration")
    return vocal_metadata, instrumental_metadata


def promote_artifacts(job: SeparationJob, asset: AudioAsset, vocals: Path, instrumental: Path, vocal_metadata: dict[str, object], instrumental_metadata: dict[str, object]) -> list[StemArtifact]:
    root = storage_root()
    final_dir = root / str(asset.user_id) / str(asset.id) / "separations" / job.fingerprint
    staging_dir = root / str(asset.user_id) / str(asset.id) / "separations" / f".{job.fingerprint}.tmp-{uuid4()}"
    staging_dir.mkdir(parents=True, exist_ok=False)
    try:
        staged_vocals = staging_dir / "vocals.wav"
        staged_instrumental = staging_dir / "instrumental.wav"
        shutil.copy2(vocals, staged_vocals)
        shutil.copy2(instrumental, staged_instrumental)
        manifest = {
            "job_id": str(job.id),
            "asset_id": str(asset.id),
            "duration_seconds": float(vocal_metadata["duration_seconds"]),
            "sample_rate": int(vocal_metadata["sample_rate"]),
            "channels": int(vocal_metadata["channels"]),
            "stems": {"vocals": "vocals.wav", "instrumental": "instrumental.wav"},
            "separator": job.separator,
            "separator_version": job.separator_version,
            "model_checkpoint": job.model_checkpoint,
            "fingerprint": job.fingerprint,
        }
        (staging_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_dir, final_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return [
        StemArtifact(job_id=job.id, stem_name="vocals", storage_key=storage_key(final_dir / "vocals.wav"), duration_seconds=float(vocal_metadata["duration_seconds"]), sample_rate=int(vocal_metadata["sample_rate"]), channels=int(vocal_metadata["channels"]), byte_size=(final_dir / "vocals.wav").stat().st_size, sha256=sha256_file(final_dir / "vocals.wav")),
        StemArtifact(job_id=job.id, stem_name="instrumental", storage_key=storage_key(final_dir / "instrumental.wav"), duration_seconds=float(instrumental_metadata["duration_seconds"]), sample_rate=int(instrumental_metadata["sample_rate"]), channels=int(instrumental_metadata["channels"]), byte_size=(final_dir / "instrumental.wav").stat().st_size, sha256=sha256_file(final_dir / "instrumental.wav")),
    ]


def execute_separation(job_id: UUID) -> None:
    db = SessionLocal()
    job: SeparationJob | None = None
    work_dir: Path | None = None
    try:
        job = db.get(SeparationJob, job_id)
        if not job or job.status != "PENDING":
            return
        asset = db.get(AudioAsset, job.asset_id)
        if not asset or asset.effective_deleted:
            raise AudioProcessingError("Audio asset is no longer available")
        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        normalized = storage_path(asset.normalized_storage_key)
        python_path, _ = runtime_paths()
        device = select_device(python_path)
        job.configuration = {**job.configuration, "device": device}
        db.commit()
        temp_root = storage_root() / ".tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        work_dir = Path(tempfile.mkdtemp(prefix=f"job-{job.id}-", dir=str(temp_root)))
        vocals, no_vocals = run_separator(normalized, work_dir / "output", device)
        vocal_metadata, instrumental_metadata = validate_stems(vocals, no_vocals, asset.duration_seconds)
        artifacts = promote_artifacts(job, asset, vocals, no_vocals, vocal_metadata, instrumental_metadata)
        db.add_all(artifacts)
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        if job is not None:
            job.status = "FAILED"
            job.error_message = exc.message if isinstance(exc, AudioProcessingError) else "Audio separation failed"
            job.error_detail = {"detail": str(exc)}
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
        db.close()


def submit_separation(job_id: UUID) -> None:
    storage_root()
    _EXECUTOR.submit(execute_separation, job_id)
