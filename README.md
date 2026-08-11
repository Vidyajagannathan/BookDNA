# BookDNA

BookDNA is a social reading platform that turns reading behaviour into a living reader identity. This repository contains a React/Vite SPA and a Python/FastAPI Cloudflare Worker backed by SQLite Durable Objects.

## Local development

Prerequisites: Node 20+, Python 3.13+, and Wrangler.

```bash
npm --prefix frontend install
npm run build
wrangler dev
```

The Worker serves the API and the built SPA on the same origin. For frontend-only work, run `npm run dev`; Vite proxies `/api` to port 8787.

## Quality checks

```bash
npm run check
npm test
```

## Deploy

Set the signing secret once, then deploy:

```bash
wrangler secret put JWT_SECRET
npm run deploy
```

Never commit `.dev.vars` or secrets. Authentication cookies are Secure in production. The Alpha vertical slice implements health, account/session foundations, Open Library search, library state, incremental DNA scoring, and the reader-facing SPA.

## Global catalog

BookDNA uses the Open Library search API for live discovery and caches normalized works in the `CATALOG_DB` D1 database. The schema separates works, editions, and identifiers so monthly Open Library dumps can grow the catalog without putting millions of records into individual user libraries.

Apply the catalog schema:

```bash
npx wrangler d1 migrations apply bookdna-catalog --local
npx wrangler d1 migrations apply bookdna-catalog --remote
```

Convert a small dump sample into importable SQL before attempting a full load:

```bash
python tools/import_openlibrary.py ol_dump_works_latest.txt.gz --type works --limit 100000 --output works.sql
npx wrangler d1 execute bookdna-catalog --remote --file works.sql
```

Edition dumps use `--type editions`. Imports are streaming and idempotent. Large production dumps should be split into bounded SQL files and loaded as a background operation; they must never run inside a web request.
