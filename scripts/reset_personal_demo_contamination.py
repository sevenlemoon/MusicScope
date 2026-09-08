"""Safely remove only the known deterministic demo data from the personal user.

Dry-run is the default. Use --apply after reviewing the counts.
"""

import argparse
from uuid import UUID

from sqlalchemy import delete, select

from app.constants import PERSONAL_USER_ID
from app.db import SessionLocal
from app.models import Artist, FeedbackEvent, ImportBatch, ListeningEvent, Memory, ProfileSnapshot, RawImportRecord, Recommendation, RecommendationRun, TimelinePeriod, Track, TrackArtist, UserTrackRelationship


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit the targeted cleanup")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        demo_track_ids = set(db.scalars(select(Track.id).where(Track.metadata_json["demo"].as_boolean() == True)).all())  # noqa: E712
        demo_artist_ids = set(db.scalars(select(Artist.id).where(Artist.canonical_name.like("Demo Artist %"))).all())
        demo_track_ids.update(db.scalars(select(Track.id).where(Track.primary_artist_id.in_(demo_artist_ids or [UUID(int=0)]))).all())
        batch_ids = set(db.scalars(select(ImportBatch.id).where(ImportBatch.user_id == PERSONAL_USER_ID, ImportBatch.source_metadata["filename"].as_string() == "deterministic-demo")).all())
        raw_ids = set(db.scalars(select(RawImportRecord.id).where(RawImportRecord.batch_id.in_(batch_ids or [UUID(int=0)]))).all())
        event_count = len(db.scalars(select(ListeningEvent.id).where(ListeningEvent.user_id == PERSONAL_USER_ID, ListeningEvent.track_id.in_(demo_track_ids or [UUID(int=0)]))).all())
        print(f"Targeting {len(demo_track_ids)} demo tracks, {len(batch_ids)} deterministic batches, {len(raw_ids)} raw records, {event_count} listening events for PERSONAL_USER_ID={PERSONAL_USER_ID}.")
        if not args.apply:
            print("Dry run only. Re-run with --apply to commit.")
            return
        db.execute(delete(FeedbackEvent).where(FeedbackEvent.user_id == PERSONAL_USER_ID, FeedbackEvent.track_id.in_(demo_track_ids or [UUID(int=0)])))
        recommendation_ids = select(Recommendation.id).join(RecommendationRun, Recommendation.run_id == RecommendationRun.id).where(RecommendationRun.user_id == PERSONAL_USER_ID, Recommendation.track_id.in_(demo_track_ids or [UUID(int=0)]))
        db.execute(delete(Recommendation).where(Recommendation.id.in_(recommendation_ids)))
        db.execute(delete(RecommendationRun).where(RecommendationRun.user_id == PERSONAL_USER_ID))
        db.execute(delete(UserTrackRelationship).where(UserTrackRelationship.user_id == PERSONAL_USER_ID, UserTrackRelationship.track_id.in_(demo_track_ids or [UUID(int=0)])))
        db.execute(delete(ListeningEvent).where(ListeningEvent.user_id == PERSONAL_USER_ID, ListeningEvent.track_id.in_(demo_track_ids or [UUID(int=0)])))
        db.execute(delete(RawImportRecord).where(RawImportRecord.id.in_(raw_ids or [UUID(int=0)])))
        db.execute(delete(ImportBatch).where(ImportBatch.id.in_(batch_ids or [UUID(int=0)])))
        db.execute(delete(Memory).where(Memory.user_id == PERSONAL_USER_ID, Memory.text.like("A demo memory attached%")))
        db.execute(delete(ProfileSnapshot).where(ProfileSnapshot.user_id == PERSONAL_USER_ID, ProfileSnapshot.features["is_demo"].as_boolean() == True))  # noqa: E712
        db.execute(delete(TimelinePeriod).where(TimelinePeriod.user_id == PERSONAL_USER_ID, TimelinePeriod.metrics["is_demo"].as_boolean() == True))  # noqa: E712
        db.execute(delete(TrackArtist).where(TrackArtist.track_id.in_(demo_track_ids or [UUID(int=0)])))
        db.execute(delete(Track).where(Track.id.in_(demo_track_ids or [UUID(int=0)])))
        db.execute(delete(Artist).where(Artist.id.in_(demo_artist_ids or [UUID(int=0)])))
        db.commit()
        print("Cleanup committed. Legitimate non-demo personal records were not targeted.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
