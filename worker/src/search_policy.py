import re


HYBRID_REMOTE_BUDGET_SECONDS = 1.5
LOCAL_FIELD_PREFIXES = ("subject:", "subject_key:", "author:")


def cache_key_url(url: str, catalog_mode: str) -> str:
    """Keep search caches isolated when the public catalog mode changes."""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}__bookdna_catalog_mode={catalog_mode}"


def remote_wait_seconds(mode: str, local_count: int) -> float | None:
    """Limit enrichment latency only when hybrid search already has results."""
    if mode in ("hybrid", "local-first") and local_count > 0:
        return HYBRID_REMOTE_BUDGET_SECONDS
    return None


def local_search_text(query: str) -> str:
    """Remove supported Open Library field syntax before querying local FTS."""
    lowered = query.casefold()
    for prefix in LOCAL_FIELD_PREFIXES:
        if lowered.startswith(prefix):
            return query[len(prefix):].strip()
    return query


def catalog_year(row: dict) -> int:
    """Return a sortable year from either API-shaped or catalog-shaped rows."""
    direct = row.get("first_publish_year") or row.get("year")
    if direct:
        try:
            return int(direct)
        except (TypeError, ValueError):
            pass
    match = re.search(r"(?:1[0-9]{3}|20[0-9]{2})", str(row.get("published") or ""))
    return int(match.group()) if match else 0


def book_fingerprint(book: dict) -> str:
    text = f'{book.get("title", "")}\x1f{book.get("author", "")}'.casefold()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def merge_books(local: list[dict], remote: list[dict], limit: int, excluded: list[dict] | None = None) -> list[dict]:
    """Keep ranked local results first and append unique remote matches."""
    output = []
    excluded = excluded or []
    seen = {book.get("id") for book in excluded if book.get("id")}
    fingerprints = {book_fingerprint(book) for book in excluded if book_fingerprint(book)}
    for book in [*local, *remote]:
        book_id = book.get("id")
        fingerprint = book_fingerprint(book)
        if not book_id or book_id in seen or (fingerprint and fingerprint in fingerprints):
            continue
        seen.add(book_id)
        if fingerprint: fingerprints.add(fingerprint)
        output.append(book)
        if len(output) >= limit:
            break
    return output
