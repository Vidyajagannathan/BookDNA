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
