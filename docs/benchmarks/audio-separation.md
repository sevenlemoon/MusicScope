# Audio separation benchmark — Milestone 6A.5

Date: 2026-09-07

## Machine and runtime

- Apple Silicon MacBook Pro, arm64
- 16 GiB RAM
- Main project Python: 3.13.3 in `.venv` (unchanged)
- Isolated audio Python: 3.12.14 in `.audio-venv312`
- FFmpeg: 9.0.1 from Homebrew
- `afconvert`: available
- Apple Silicon MPS: available through PyTorch

## Probe

```bash
.venv/bin/python scripts/audio_benchmark.py
```

The probe generated a deterministic 10-second synthetic WAV mix in a
temporary directory. It used no external audio and did not download model
weights.

## Candidate installation results

### First candidate: demucs-mlx 1.4.4

This Apple-Silicon-native package was selected as the first candidate because
it avoids PyTorch at inference time. Installation failed while building its
`mlx-audio-io` dependency: the local Command Line Tools do not contain the
required C++ standard headers (`cstddef`), and Ninja was not installed. No
system compiler/toolchain expansion was made for this validation.

### One permitted alternative: demucs-infer 4.2.0

This inference-only maintained fork installed successfully in the isolated
Python 3.12 environment. Its package metadata reports MIT licensing and its
pretrained registry downloads `htdemucs` from:

```text
https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th
```

The downloaded checkpoint was 80.2 MB and had SHA-256:

```text
8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4
```

Recorded packages:

| Package | Version |
|---|---:|
| demucs-infer | 4.2.0 |
| torch | 2.14.0 |
| torchaudio | 2.11.0 |
| soundfile | 0.14.0 |
| numpy | 2.5.3 |

## Runnable benchmark result

Command used:

```bash
.audio-venv312/bin/python scripts/run_audio_separator_benchmark.py --durations 10 30
```

The benchmark created deterministic synthetic music-like WAV fixtures at
44.1 kHz stereo. It used `htdemucs`, one shift, 7-second segments, and MPS.
It is a runtime/output compatibility test, not a subjective quality study.

| Fixture | Processing | RTF | Device | Peak child memory |
|---:|---:|---:|---|---:|
| 10 s | 4.875 s | 0.4875 | MPS | 905.1 MB |
| 30 s | 5.241 s | 0.1747 | MPS | 905.1 MB |

The first run included model download/warm-up and is not included in the
reported processing timings. The 30-second run completed in reasonable time.

Both runs produced:

- `vocals.wav`: 44.1 kHz, stereo, PCM signed 16-bit, matching input duration;
- `no_vocals.wav`, mapped by the adapter to instrumental/accompaniment: 44.1
  kHz, stereo, PCM signed 16-bit, matching input duration;
- equal duration, sample rate, and channel count for synchronized playback.

The benchmark confirms runnable output compatibility, but synthetic fixtures
cannot establish real musical separation quality.

## Final 6A.5 decision

**APPROVE_FOR_MVP** — use `demucs-infer==4.2.0` with the `htdemucs` checkpoint
and MPS when available. Fall back to CPU only as an explicit runtime setting;
do not silently claim acceleration when MPS is unavailable.

The exact future invocation is:

```bash
.audio-venv312/bin/demucs-infer \
  -n htdemucs -d mps \
  --two-stems vocals --other-method add \
  --shifts 1 --segment 7 \
  -o <output-directory> <normalized-input.wav>
```

`vocals.wav` is the vocal stem. `no_vocals.wav` is the generated
instrumental/accompaniment stem and should be exposed by MusicScope as
`instrumental.wav` in its manifest. Spleeter is not the default fallback.
