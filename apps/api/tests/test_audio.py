import io
import shutil
import wave
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.audio import NORMALIZATION_CONFIG, execute_separation, separation_fingerprint, validate_stems
from app.db import SessionLocal
from app.main import app
from app.models import AudioAsset, User


client = TestClient(app)


def wav_bytes(duration_seconds: float = 0.05) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * int(8000 * duration_seconds))
    return output.getvalue()


def test_separation_fingerprint_is_stable_and_changes_with_source() -> None:
    first = AudioAsset(user_id=uuid4(), original_filename="a.wav", source_storage_key="a", normalized_storage_key="b", source_sha256="a" * 64, source_size_bytes=10, duration_seconds=1, sample_rate=44100, channels=2)
    second = AudioAsset(user_id=first.user_id, original_filename="other-name.wav", source_storage_key="different", normalized_storage_key="different", source_sha256="a" * 64, source_size_bytes=10, duration_seconds=1, sample_rate=44100, channels=2)
    changed = AudioAsset(user_id=first.user_id, original_filename="a.wav", source_storage_key="a", normalized_storage_key="b", source_sha256="b" * 64, source_size_bytes=10, duration_seconds=1, sample_rate=44100, channels=2)
    assert separation_fingerprint(first) == separation_fingerprint(second)
    assert separation_fingerprint(first) != separation_fingerprint(changed)
    assert NORMALIZATION_CONFIG["sample_rate"] == 44100


def test_stem_validation_rejects_missing_files(tmp_path: Path) -> None:
    try:
        validate_stems(tmp_path / "vocals.wav", tmp_path / "instrumental.wav", 1)
    except Exception as exc:
        assert "empty" in str(exc).lower() or "missing" in str(exc).lower()
    else:
        raise AssertionError("missing stems should fail validation")


def test_upload_normalizes_and_persists_audio_asset(monkeypatch) -> None:
    monkeypatch.setattr("app.routes.submit_separation", lambda _job_id: None)
    response = client.post("/api/v1/audio-assets", files={"file": ("demo.wav", wav_bytes(), "audio/wav")})
    assert response.status_code == 201
    payload = response.json()
    assert payload["sample_rate"] == 44100
    assert payload["channels"] == 2
    assert payload["duration_seconds"] > 0
    assert client.delete(f"/api/v1/audio-assets/{payload['id']}").status_code == 204


def test_non_audio_upload_is_rejected() -> None:
    response = client.post("/api/v1/audio-assets", files={"file": ("not-audio.wav", b"not audio", "audio/wav")})
    assert response.status_code == 400


def test_fake_separator_lifecycle_manifest_and_artifact(monkeypatch) -> None:
    monkeypatch.setattr("app.routes.submit_separation", lambda _job_id: None)

    upload = client.post("/api/v1/audio-assets", files={"file": ("lifecycle.wav", wav_bytes(), "audio/wav")})
    asset_id = upload.json()["id"]
    start = client.post(f"/api/v1/audio-assets/{asset_id}/separate")
    assert start.status_code == 202
    job_id = start.json()["id"]

    def fake_separator(input_path: Path, output_dir: Path, _device: str) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True)
        vocals = output_dir / "vocals.wav"
        instrumental = output_dir / "no_vocals.wav"
        shutil.copy2(input_path, vocals)
        shutil.copy2(input_path, instrumental)
        return vocals, instrumental

    monkeypatch.setattr("app.audio.runtime_paths", lambda: (Path("/bin/true"), Path("/bin/true")))
    monkeypatch.setattr("app.audio.select_device", lambda _python_path: "cpu")
    monkeypatch.setattr("app.audio.run_separator", fake_separator)
    execute_separation(UUID(job_id))

    status = client.get(f"/api/v1/separation-jobs/{job_id}")
    assert status.json()["status"] == "COMPLETED"
    cached = client.post(f"/api/v1/audio-assets/{asset_id}/separate")
    assert cached.status_code == 202
    assert cached.json()["id"] == job_id
    manifest = client.get(f"/api/v1/separation-jobs/{job_id}/manifest")
    assert manifest.status_code == 200
    assert set(manifest.json()["stems"]) == {"vocals", "instrumental"}
    artifact = client.get(f"/api/v1/separation-jobs/{job_id}/artifacts/vocals")
    assert artifact.status_code == 200
    assert client.delete(f"/api/v1/audio-assets/{asset_id}").status_code == 204


def test_separator_failure_is_exposed_without_artifacts(monkeypatch) -> None:
    monkeypatch.setattr("app.routes.submit_separation", lambda _job_id: None)
    upload = client.post("/api/v1/audio-assets", files={"file": ("failure.wav", wav_bytes(), "audio/wav")})
    asset_id = upload.json()["id"]
    start = client.post(f"/api/v1/audio-assets/{asset_id}/separate")
    job_id = start.json()["id"]
    monkeypatch.setattr("app.audio.runtime_paths", lambda: (_ for _ in ()).throw(RuntimeError("runtime missing")))
    execute_separation(UUID(job_id))
    status = client.get(f"/api/v1/separation-jobs/{job_id}")
    assert status.json()["status"] == "FAILED"
    assert client.get(f"/api/v1/separation-jobs/{job_id}/manifest").status_code == 409
    assert client.delete(f"/api/v1/audio-assets/{asset_id}").status_code == 204


def test_audio_models_are_importable() -> None:
    db = SessionLocal()
    try:
        user = db.get(User, uuid4())
        assert user is None
    finally:
        db.close()
