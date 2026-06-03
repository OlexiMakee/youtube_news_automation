# news_scraper/connectors/ (Phase 1 Connector Layer)

Modular connector implementations for governed source ingestion.

## Status

Implemented as a migration-safe normalization layer. Connectors parse or fetch
source data and return `SourceRecord` payloads shaped for the future
`source_records` table. They do not write to the live database.

## Directory Structure

```
news_scraper/connectors/
├── __init__.py
├── base.py              # ConnectorContext, SourceRecord, ConnectorFetchResult
├── registry.py          # Safe metadata + connector factory
├── youtube_connector.py # Existing scraper-engine adapter, no direct DB write
├── rss_connector.py     # RSS/Atom parser using stdlib XML
├── manual_connector.py  # CSV/JSON batch import parser
└── README.md
```

## Connector Contract

All connectors receive non-secret `ConnectorContext` and return
`ConnectorFetchResult`:

```python
context = ConnectorContext(
    source_id=1,
    source_type="rss",
    name="Example Feed",
    policy_tier="C",
    source_url="https://example.com/feed.xml",
)
result = RSSConnector(context).fetch(xml_text=fixture_xml)
rows = [record.to_db_dict() for record in result.records]
summary = result.audit_summary()
```

Each record maps to:
- `source_id`
- `external_record_id`
- `record_type`
- `title`
- `url`
- `published_at`
- `content_hash`
- `metadata_json`

## Implemented Connectors

### YouTubeConnector

- Uses the existing `YouTubeScraperEngine` through an in-memory capture storage.
- Normalizes video rows to `record_type="video"`.
- Defaults to Tier E because this path adapts the current scraper engine, not the official YouTube Data API.
- Does not expose or require secret values.
- Does not write to `videos` or `source_records`.

### RSSConnector

- Parses RSS 2.0 and Atom from XML text.
- Can download a feed URL with stdlib `urllib`.
- Normalizes entries to `record_type="article"`.
- Rejects malformed entries without rejecting the whole feed when possible.

### ManualConnector

- Parses JSON lists, JSON objects with `records` or `items`, and CSV files.
- Requires `title`, `url`, and `published_at`.
- Normalizes rows to `record_type="manual_upload"`.
- Reports rejected rows in the fetch result.

---

## Policy Guardrails

- Tier X sources are rejected before fetch.
- Connector metadata reports `writes_live_database=false`.
- Secret values are not accepted by the base context or registry metadata.
- Live DB persistence waits for explicit migration and route wiring approval.

## Testing

- `scratch/test_connectors.py`
- `python -m unittest scratch.test_connectors`

## Next Wiring Step

When the governance registry migration is explicitly applied, add a persistence
service that inserts `record.to_db_dict()` into `source_records` and writes a
matching `connector_runs` audit row. Keep that route admin-gated.
