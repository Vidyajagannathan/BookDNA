# BookDNA

BookDNA is a social reading platform that turns reading behaviour into a living reader identity. This repository contains a React/Vite SPA and a Python/FastAPI Cloudflare Worker backed by SQLite Durable Objects.

## Local development

Prerequisites: Node 20+, Python 3.13+, and Wrangler.

```bash
npm --prefix frontend install
npm run setup:python
npm run build
wrangler dev
```

The Worker serves the API and the built SPA on the same origin. For frontend-only work, run `npm run dev`; Vite proxies `/api` to port 8787.

## Quality checks

```bash
npm run check
npm test
```

On macOS, if `python3.13` is missing, install it with `brew install python@3.13`. The project-local `.venv` keeps BookDNA's supported Python and catalog dependencies separate from the system Python.

Set `ADMIN_USER_IDS` to a comma-separated list of BookDNA user IDs to grant access to the private `/admin` dashboard. Keep this value out of source control in production.

## Deploy

Set the signing secret once, then deploy:

```bash
wrangler secret put JWT_SECRET
npm run deploy
```

Never commit `.dev.vars` or secrets. Authentication cookies are Secure in production. The Alpha vertical slice implements health, account/session foundations, Open Library search, library state, incremental DNA scoring, and the reader-facing SPA.

## Global catalog

The catalog builder combines Open Library, Library of Congress MARC, Crossref book types, DataCite Books, DOAB, and Project Gutenberg without paid metadata APIs. It keeps source claims and deterministic work/edition identifiers in DuckDB, exports an 8 GiB-capped Zstandard Parquet archive, and fills eight 400 MiB-capped D1 FTS shards in quality order. Open Library remains the live fallback.

Use temporary storage outside the repository. The pipeline refuses to exceed 140 GiB and can resume source ingestion safely:

```bash
python -m pip install -e .
CATALOG_WORK=/tmp/bookdna-catalog
python -m catalog_pipeline --workspace "$CATALOG_WORK" download \
  https://openlibrary.org/data/ol_dump_editions_latest.txt.gz "$CATALOG_WORK/openlibrary-editions.txt.gz"
python -m catalog_pipeline --workspace "$CATALOG_WORK" ingest openlibrary "$CATALOG_WORK/openlibrary-editions.txt.gz"
python -m catalog_pipeline --workspace "$CATALOG_WORK" ingest loc "$CATALOG_WORK/BooksAll.2016.part01.utf8.gz"
python -m catalog_pipeline --workspace "$CATALOG_WORK" fetch crossref "$CATALOG_WORK/crossref.jsonl"
python -m catalog_pipeline --workspace "$CATALOG_WORK" fetch datacite "$CATALOG_WORK/datacite.jsonl"
python -m catalog_pipeline --workspace "$CATALOG_WORK" fetch doab "$CATALOG_WORK/doab.jsonl"
python -m catalog_pipeline --workspace "$CATALOG_WORK" ingest gutenberg "$CATALOG_WORK/pg_catalog.csv"
python -m catalog_pipeline --workspace "$CATALOG_WORK" report
python -m catalog_pipeline --workspace "$CATALOG_WORK" export-archive "$CATALOG_WORK/archive"
python -m catalog_pipeline --workspace "$CATALOG_WORK" export-d1 "$CATALOG_WORK/d1"
python -m catalog_pipeline --workspace "$CATALOG_WORK" export-identifiers "$CATALOG_WORK/d1/identifiers.sql"
```

Apply `migrations/` only to `bookdna-catalog`; `schema/search.sql` and `schema/identifiers.sql` are templates for their dedicated databases. Load generated SQL with `wrangler d1 execute`. Full exports replace a shard atomically at file scope; use `--incremental` only for bounded refresh batches.

The control setting `catalog_settings.mode` provides rollout and rollback:

- `shadow`: execute local queries for validation but return Open Library results.
- `hybrid` or `local-first`: return local results first and federate to Open Library when needed.
- `fallback`: effectively disables local search.

R2 must be enabled by the Cloudflare account owner before the archive can be uploaded. Do not accept billing terms automatically. Once enabled, create a private bucket, add its Worker binding, upload only `archive/`, and record the byte count in `catalog_settings`; the exporter will stop before 8 GiB. Book content and bulk cover images are never downloaded by this pipeline.

Useful endpoints are `/api/books/search`, `/api/books/{work_id}`, `/api/books/{work_id}/editions`, `/api/books/isbn/{isbn}`, and `/api/books/catalog/status`.
