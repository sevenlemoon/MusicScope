# Lightweight concert discovery

## Provider decision

MusicScope uses a small internal `ConcertProvider` boundary. The selected
optional live adapter is Ticketmaster Discovery because its documented API
supports attraction/artist search, upcoming event search, venue/location data,
dates, and an external event URL. It requires an API key and documents default
quotas, so it is never required for the graduation demo. The focused milet
example also uses a small official-source adapter for the structured schedule
at the [official milet tour page](https://fc.milet.jp/s/n114/page/tour-2026?ima=0000&link=ROBO004).
This is an artist-specific adapter, not a general web-scraping framework.

Songkick supports artist-name event search but requires an application key and
currently states that student, educational, and hobby API requests are not
being approved. Bandsintown exposes artist events with date/time, venue,
location, and links but requires an application ID. These were not added as
additional adapters.

References: [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/),
[Songkick API access](https://www.songkick.com/developer),
[Bandsintown API documentation](https://help.artists.bandsintown.com/en/articles/9186477-api-documentation).

## Credentials and fallback

Default configuration:

```text
CONCERT_PROVIDER=demo
TICKETMASTER_API_KEY=
CONCERT_CACHE_HOURS=6
```

Set `CONCERT_PROVIDER=ticketmaster` and provide `TICKETMASTER_API_KEY` only
when generic live lookups are desired. The milet official adapter is selected
automatically for a milet search. Normal/live searches never fall back to
fictional events: provider errors return fresh/stale cached events where
possible, otherwise the API returns an unavailable/no-results state. Demo
fixtures require the explicit `demo=true` query parameter and are labeled as
演示数据 / demo data.

## Domain and matching

`ConcertEvent` points to an existing MusicScope `Artist`. Provider-specific
artist identifiers are stored in `ArtistProviderIdentity`; they never create a
second canonical artist. Matching is first by the normalized MusicScope artist
name and then by the provider identifier once resolved. No ML entity
resolution is used.

The event domain stores date, optional doors/open and exact start time, timezone, venue, city,
region, country, optional coordinates, external URL, provider, status, and
fetch timestamp. Missing time or venue fields remain missing; the UI does not
invent them.

## Cache and demo data

Concert events are stored in PostgreSQL and refreshed at most once per six
hours per artist unless `force_refresh=true` is requested. The deterministic
demo provider includes fictional events for Demo Artists 01–03, including a
full date/time event, date-only events, multiple events for one artist,
different cities/countries, and an artist with no events. Demo cards are
explicitly labeled as fictional fixtures and never expose their internal
placeholder URLs. Live events only show a details link when a legitimate
provider or official URL exists. Provider images are used when supplied;
otherwise the UI shows a neutral placeholder.

Relevant artists are derived from existing effective User–Track Relationships:
favorites are prioritized, followed by play count and recency. No separate
concert recommendation algorithm is introduced.

## API

- `GET /api/v1/artists/{artist_id}/concerts`
- `GET /api/v1/concerts`
- `GET /api/v1/concerts/search?artist=milet`

Both endpoints return normalized internal event objects and provider/cache
status. The search endpoint also accepts `demo=true` for an explicit offline
fixture view. MusicScope only exposes a `View details` external link;
ticketing and checkout are outside scope.
