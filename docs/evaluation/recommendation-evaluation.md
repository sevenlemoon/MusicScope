# Recommendation MVP evaluation

This bounded evaluation uses the deterministic demo catalog and the same
`generate_recommendations` pipeline used by the API. It requests 12 tracks at
exploration levels 10, 50, and 90. Re-run it with `make recommendation-evaluation`.

| Exploration | Role composition | Unique artists | Unique genres | Max artist share | Mean novelty | Unfamiliar artist ratio |
|---:|---|---:|---:|---:|---:|---:|
| 10 | 6 precise, 4 adjacent, 2 bold | 11 | 8 | 16.7% | 0.542 | 16.7% |
| 50 | 4 precise, 4 adjacent, 4 cross-boundary | 10 | 8 | 16.7% | 0.667 | 33.3% |
| 90 | 1 precise, 3 adjacent, 8 cross-boundary | 8 | 6 | 25.0% | 0.778 | 66.7% |

All three runs had complete explanation evidence. The selected track IDs also
changed between levels, so the outputs are not merely reordered copies. The
results demonstrate the intended direction: higher exploration increases
novelty and cross-boundary roles while the deterministic diversity pass keeps
artist concentration bounded. This is a functional demonstration, not a
quality or user-preference study.

The evaluation creates inspectable `RecommendationRun` records by design. It
does not change the user's exploration setting or add feedback.
