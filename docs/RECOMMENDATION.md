# Recommendation Design v1.0

## MVP goal
Produce demonstrably personalized, explainable recommendations without requiring a production-scale collaborative-filtering dataset.

## Pipeline
1. Build long-term profile from historical effective behavior.
2. Build short-term state using a configurable recent window and recency decay.
3. Generate candidates from metadata/content similarity and adjacent artists/tracks available in the catalog/provider.
4. Score candidates.
5. Apply exploration transformation.
6. Diversify/re-rank.
7. Assign recommendation role.
8. Generate explanation from stored evidence.
9. Record run and user feedback.

## Conceptual score
final_score =
  w_long * long_term_match +
  w_short * short_term_match +
  w_relation * relationship_signal +
  w_quality * candidate_quality +
  exploration_adjustment -
  repetition_penalty -
  negative_feedback_penalty

Then apply diversity constraints/re-ranking.

Do not treat this formula as immutable; implement weights/configuration cleanly so it can be evaluated.

## Exploration
Exploration level affects:
- distance from profile centroid
- proportion of unfamiliar artists/genres
- role quotas
- novelty bonus

It should not simply add random songs.

## Feedback semantics
Implicit:
- completion
- replay
- skip timing
- repeated skips
- save/favorite

Explicit:
- like/dislike
- skip reason

“Not for today” should mainly affect short-term state.
“Simply dislike” should have stronger long-term impact.

## Evaluation
Include offline/demo metrics:
- relevance proxy
- catalog/artist diversity
- novelty
- repeat rate
- acceptance/completion where available
- explanation coverage

## Implemented MVP pipeline

The initial implementation keeps each stage deterministic and inspectable:

1. Candidate generation reads canonical tracks, catalog genres, effective user relationships, and feedback.
2. Scoring combines normalized long-term affinity, short-term affinity, relationship signals, novelty, repetition penalty, and negative-feedback penalty.
3. Exploration changes the centralized weight balance between profile match and novelty.
4. Role assignment uses measurable match and novelty thresholds for Precise Match, Adjacent Exploration, Cross-boundary Discovery, and Bold Try.
5. Diversity selection applies role quotas plus artist and genre caps.
6. Explanations are generated from the stored score breakdown and evidence signals.

The MVP does not use embeddings, collaborative filtering, LLM ranking, or random candidate injection. A 0–100 exploration level is stored on each recommendation run and is never silently changed by the system.
