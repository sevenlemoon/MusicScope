# Audio Source Separation — MVP

## Decision boundary

The validated local MVP target is:

```text
audio input -> 2-stem separation -> cached vocals + instrumental
             -> synchronized playback -> independent gain controls
```

Neural separation while playback is already running is explicitly a stretch
goal and must not block the preprocessed-stem MVP.

## Current environment

Validation was run on an Apple Silicon MacBook Pro (arm64, 16 GiB RAM) with
Python 3.13.3 in the project virtual environment. The main environment was
not changed. Audio inference runs in a separate `.audio-venv312` using Python
3.12.14. The host now has Homebrew FFmpeg 9.0.1.

The isolated audio environment has:

- `demucs-infer==4.2.0`;
- `torch==2.14.0` and `torchaudio==2.11.0`;
- `soundfile==0.14.0` for WAV output;
- MPS built and available on Apple Silicon;
- the downloaded `htdemucs` checkpoint.

The first `demucs-mlx==1.4.4` candidate was not usable because its
`mlx-audio-io` native build failed on missing C++ headers. The one permitted
alternative, `demucs-infer`, installed and benchmarked successfully. The
original Meta repository is archived; the selected package is the maintained
inference-oriented fork documented at
[demucs-infer on PyPI](https://pypi.org/project/demucs-infer/4.2.0/) and
[its source repository](https://github.com/openmirlab/demucs-infer).

The dependency-free probe is reproducible with:

```bash
.venv/bin/python scripts/audio_benchmark.py
```

It generates a short project-owned synthetic WAV fixture and reports whether
the prerequisites for a real separator run are present. It does not download
models or use copyrighted audio.

## Candidate review

| Candidate | Fit for 2-stem MVP | Practical assessment |
|---|---|---|
| `demucs-infer==4.2.0` with `htdemucs` | Selected | Runnable on isolated Python 3.12 with PyTorch MPS; passed 10-second and 30-second output compatibility benchmarks. |
| `demucs-mlx==1.4.4` | Rejected for now | Attractive native MLX path, but installation requires a native `mlx-audio-io` build that failed against the current Command Line Tools. |
| Spleeter 2-stem | Not selected | Older TensorFlow/Python constraints were not worth a third runtime attempt after the successful Demucs-compatible alternative. |
| MDX-family checkpoints | Deferred | No comparison was needed after the selected runtime passed the bounded MVP gate. |

The selected package retains the upstream Demucs `htdemucs` model and exposes
the same two-stem mode while providing a modern inference-only package path.
The original Demucs repository itself records that it is no longer actively
maintained, which is why the archived package was not used directly:
[original Demucs repository](https://github.com/facebookresearch/demucs),
[demucs-infer PyPI](https://pypi.org/project/demucs-infer/4.2.0/).

## Runnable benchmark result

The bounded benchmark used deterministic 10-second and 30-second synthetic
music-like WAV fixtures. It ran with `htdemucs`, MPS, one shift, and 7-second
segments. Results:

| Duration | Processing | RTF | Output validation |
|---:|---:|---:|---|
| 10 s | 4.875 s | 0.4875 | vocals + no_vocals, both 44.1 kHz stereo PCM, 10 s |
| 30 s | 5.241 s | 0.1747 | vocals + no_vocals, both 44.1 kHz stereo PCM, 30 s |

Measured peak child memory was 905.1 MB. PyTorch reported MPS built and
available, and the benchmark explicitly used `-d mps`. These synthetic tests
validate runtime and synchronized-output compatibility, not subjective music
quality.

## Final selection

**APPROVE_FOR_MVP:** use `demucs-infer==4.2.0`, `htdemucs`, and MPS on this
development machine. CPU is an explicit fallback. Spleeter is not the default
fallback.

Exact future command:

```bash
.audio-venv312/bin/demucs-infer -n htdemucs -d mps \
  --two-stems vocals --other-method add --shifts 1 --segment 7 \
  -o <output-directory> <normalized-input.wav>
```

The package is MIT-licensed. The model is the upstream `htdemucs` checkpoint
downloaded from the Demucs public model host; its exact URL and SHA-256 are
recorded in `docs/benchmarks/audio-separation.md`. Final product distribution
should keep the package/model attribution in the project notices.

## Implemented preprocessing and pipeline

The implementation uses one small service module, not a service mesh:

```text
upload -> validate size/type/duration
       -> FFmpeg normalize to canonical WAV
       -> create SeparationJob(PENDING)
       -> simple database-backed worker claims job
       -> selected separator writes vocals + instrumental atomically
       -> write manifest and mark COMPLETED
```

The job states are `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED`. A
failure stores a safe user-facing message plus diagnostic details for local
logs. No Redis, Celery, or extra queue infrastructure is needed initially.

FFmpeg is the intended normalizer because its documented resampler handles
sample-rate conversion, channel rematrixing, and sample-format conversion:
[FFmpeg resampler documentation](https://ffmpeg.org/ffmpeg-resampler.html).
The proposed canonical input/output is stereo PCM WAV at 44.1 kHz, with a
maximum upload size of 250 MB and a maximum duration of 15 minutes for the
local MVP. These limits should be enforced before invoking a model.

## Cache and storage design

The local filesystem adapter stores artifacts outside the source tree:

```text
storage/audio/{user_id}/{asset_id}/source.wav
storage/audio/{user_id}/{asset_id}/separations/{fingerprint}/vocals.wav
storage/audio/{user_id}/{asset_id}/separations/{fingerprint}/instrumental.wav
storage/audio/{user_id}/{asset_id}/separations/{fingerprint}/manifest.json
```

The cache fingerprint should be:

```text
SHA256(source_bytes)
 + separator_name/version
 + model/checkpoint identifier
 + stem_mode
 + normalization settings
 + output format settings
```

The database stores the fingerprint, job state, manifest metadata, and logical
storage references; it does not store large audio blobs. Writes go to a
temporary directory and are renamed into place only after both stems and the
manifest validate. This prevents a partial separation from becoming a cache
hit.

## Browser playback implementation

The player decodes both cached stems into one `AudioContext`, creates a
new `AudioBufferSourceNode` for each playback attempt, connect each source to
its own `GainNode`, then connect both gains to the same destination. Both
sources start at the same `audioContext.currentTime + small_lead_in` and the
same buffer offset. The Web Audio API supports scheduled starts with a shared
context timebase; a source node is one-shot, so pause/seek creates new source
nodes. See [MDN AudioBufferSourceNode.start()](https://developer.mozilla.org/en-US/docs/Web/API/AudioBufferSourceNode/start).

Transport state is `{playing, offset, startedAt}`. On pause, calculate the
offset from the shared clock and stop both nodes. On seek, stop both and
recreate them at the requested offset. `Promise.all` loads/decodes both stems;
if either fails, the UI reports one failed playback state rather than playing
an incomplete pair. Browser autoplay suspension must be resumed from a user
gesture.

This gives synchronized playback and independent vocal/instrumental gain
control without neural inference during playback. The future progressive
experiment would require chunk boundaries, overlap/add handling, buffering,
underrun measurement, and a worker/GPU strategy; it is intentionally deferred.

## Implemented API surface

These endpoints form the implemented audio boundary:

- `POST /api/v1/audio-assets` — upload and validate an input.
- `POST /api/v1/audio-assets/{asset_id}/separate` — create or reuse a cached
  separation job.
- `GET /api/v1/separation-jobs/{job_id}` — state, progress, and failure info.
- `GET /api/v1/separation-jobs/{job_id}/manifest` — completed stem metadata
  and playback URLs.
- `GET /api/v1/separation-jobs/{job_id}/artifacts/{stem_name}` — controlled
  WAV artifact serving.
- `GET /api/v1/audio-assets` — list active user-scoped assets.
- `DELETE /api/v1/audio-assets/{asset_id}` — delete an asset and its artifacts.

The APIs remain user-scoped even though the first demo is local and
single-user. They must not expose filesystem paths directly.

## Security, cleanup, and test coverage

The implementation rejects path traversal, enforces upload size and duration
limits, does not trust client MIME types alone, and cleans abandoned temporary
files. Source and generated files are user-owned and deletable without
touching other users' directories.

Backend tests cover file validation, fingerprint determinism, normalization,
fake job execution, manifest generation, artifact serving, and cleanup.
Frontend tests verify that both sources receive the same start offset and that
transport state survives pause/seek while gain changes remain independent.

## Milestone 6B implementation

The approved MVP implementation now includes:

- `AudioAsset`, `SeparationJob`, and `StemArtifact` persistence;
- migration `0006_audio_separation`;
- local server-controlled storage under `storage/audio/{user_id}/{asset_id}`;
- FFprobe validation and deterministic FFmpeg normalization;
- a SHA-256/configuration separation fingerprint and completed-job cache reuse;
- a one-worker in-process background runner with `PENDING`, `PROCESSING`,
  `COMPLETED`, and `FAILED` states;
- controlled manifest and WAV artifact endpoints;
- a synchronized Web Audio player using one `AudioContext`, two gain nodes,
  shared play/pause/seek transport, and independent vocal/instrumental gain;
- fake-separator unit coverage plus one real smoke path.

The real smoke test is:

```bash
PYTHONPATH=apps/api .venv/bin/python scripts/audio_smoke.py
```

The smoke path uses a short generated WAV, so it does not require copyrighted
audio. It invokes the isolated `.audio-venv312` runtime through the API worker.

The implementation intentionally excludes 4-stem mode, live microphone input,
true streaming separation, cloud GPUs, external storage, waveform editing,
and Milestone 7 concert discovery.
