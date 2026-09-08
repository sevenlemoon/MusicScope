from app.importer import detect_version, normalize_text, parse_csv, parse_datetime, parse_playlist_text
from fastapi.testclient import TestClient
from app.main import app


def test_normalization_handles_case_spacing_and_punctuation() -> None:
    assert normalize_text("  Björk — Jóga  ") == "bjork joga"
    assert normalize_text("The  Artist & Co.") == "the artist and co"


def test_version_detection_preserves_variant_signal() -> None:
    assert detect_version("Song (Live)") == "live"
    assert detect_version("Song [Remix]") == "remix"
    assert detect_version("Song") == "original"


def test_csv_parser_and_datetime_are_tolerant() -> None:
    rows = parse_csv("artist,title,played_at\nArtist,Song,2025-01-02T03:04:05Z\n")
    assert rows[0]["title"] == "Song"
    assert parse_datetime(rows[0]["played_at"]) is not None
    assert parse_datetime("not a date") is None


def test_netease_playlist_import_reports_unsupported_complete_track_list() -> None:
    response = TestClient(app).post("/api/v1/imports/playlist-url", json={"url": "https://music.163.com/m/playlist?id=5036528042"})
    assert response.status_code == 503
    assert "complete track list" in response.json()["detail"]


def test_playlist_text_parser_skips_blank_lines_and_preserves_playlist_only_semantics() -> None:
    rows, invalid = parse_playlist_text("Song – Artist / Guest\n\nnot a track line\n")
    assert rows[0]["title"] == "Song"
    assert rows[0]["artists"] == ["Artist", "Guest"]
    assert "played_at" not in rows[0]
    assert invalid == ["not a track line"]


def test_playlist_text_parser_handles_real_samples_unicode_and_2500_rows() -> None:
    samples = [
        "Can We Kiss Forever? - Kina",
        "Monody (Radio Edit) - TheFatRat / Laura Brehm",
        "Need You Right Now - HEDEGAARD / Hayley Warner",
        "Superficial Love - Karim Mika / Gabs",
        "Neon Rainbow - Rameses B / Anna Yvette",
        "Tattoo - GJan",
        "Immediate Approach - 川越康弘 / 南亜矢子",
        "Savage Love (Laxed – Siren Beat) (BTS Remix) - Jawsh 685 / Jason Derulo / BTS",
        'Hopes and Dreams (From "Undertale") - Tenkitsune',
    ]
    content = "\n".join(samples + [f"Synthetic Track {index} - Artist {index % 50}" for index in range(2491)])
    rows, invalid = parse_playlist_text(content)
    assert len(rows) == 2500
    assert invalid == []
    assert rows[1]["artists"] == ["TheFatRat", "Laura Brehm"]
    assert rows[7]["title"] == "Savage Love (Laxed – Siren Beat) (BTS Remix)"
    assert rows[8]["artist"] == "Tenkitsune"
    assert rows[8]["title"] == 'Hopes and Dreams (From "Undertale")'
    assert rows[6]["artists"] == ["川越康弘", "南亜矢子"]
    ambiguous_rows, _ = parse_playlist_text("Song - Earth, Wind & Fire")
    assert ambiguous_rows[0]["artists"] == ["Earth, Wind & Fire"]
