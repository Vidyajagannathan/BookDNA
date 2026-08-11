from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re
import unicodedata

SOURCE_PRIORITY = {"doab": 60, "crossref": 55, "datacite": 55, "loc": 50, "openlibrary": 40, "gutenberg": 30}


def clean(value) -> str | None:
    text = " ".join(str(value or "").replace("\x00", "").split()).strip()
    return text or None


def normalized_text(value) -> str:
    text = unicodedata.normalize("NFKD", clean(value) or "").casefold()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def isbn13_valid(value: str) -> bool:
    return len(value) == 13 and value.isdigit() and sum((1 if i % 2 == 0 else 3) * int(n) for i, n in enumerate(value)) % 10 == 0


def isbn10_valid(value: str) -> bool:
    if len(value) != 10 or not value[:9].isdigit() or not (value[-1].isdigit() or value[-1] == "X"):
        return False
    return sum((10 - i) * (10 if n == "X" else int(n)) for i, n in enumerate(value)) % 11 == 0


def normalize_isbn(value) -> str | None:
    raw = re.sub(r"[^0-9X]", "", str(value or "").upper())
    if isbn13_valid(raw):
        return raw
    if not isbn10_valid(raw):
        return None
    stem = "978" + raw[:9]
    check = (10 - sum((1 if i % 2 == 0 else 3) * int(n) for i, n in enumerate(stem)) % 10) % 10
    return stem + str(check)


def stable_id(prefix: str, *parts) -> str:
    payload = "\x1f".join(normalized_text(part) for part in parts)
    return f"{prefix}_{sha256(payload.encode()).hexdigest()[:24]}"


@dataclass(slots=True)
class CanonicalRecord:
    source: str
    source_id: str
    title: str
    kind: str = "edition"
    authors: list[str] = field(default_factory=list)
    contributors: list[dict] = field(default_factory=list)
    publisher: str | None = None
    published: str | None = None
    language: str | None = None
    format: str | None = None
    description: str | None = None
    subjects: list[str] = field(default_factory=list)
    identifiers: dict[str, list[str]] = field(default_factory=dict)
    cover_url: str | None = None
    access_url: str | None = None
    work_hint: str | None = None

    def normalized(self) -> "CanonicalRecord":
        ids = {str(k).lower(): sorted({clean(v) for v in values if clean(v)}) for k, values in self.identifiers.items()}
        isbns = sorted({isbn for value in ids.get("isbn", []) if (isbn := normalize_isbn(value))})
        if "isbn" in ids:
            if isbns: ids["isbn"] = isbns
            else: ids.pop("isbn")
        return CanonicalRecord(
            source=self.source.lower(), source_id=clean(self.source_id) or "", title=clean(self.title) or "", kind=self.kind if self.kind in ("work","edition") else "edition",
            authors=[v for value in self.authors if (v := clean(value))], contributors=self.contributors,
            publisher=clean(self.publisher), published=clean(self.published), language=clean(self.language), format=clean(self.format),
            description=clean(self.description), subjects=[v for value in self.subjects if (v := clean(value))][:100], identifiers=ids,
            cover_url=clean(self.cover_url), access_url=clean(self.access_url), work_hint=clean(self.work_hint),
        )

    @property
    def isbn13(self) -> str | None:
        return next(iter(self.identifiers.get("isbn", [])), None)

    @property
    def work_id(self) -> str:
        if self.source == "openlibrary" and self.work_hint:
            return "work_ol_" + normalized_text(self.work_hint).replace(" ", "_")
        return stable_id("work", self.title, self.authors[0] if self.authors else "", self.language or "und")

    @property
    def edition_id(self) -> str:
        if self.isbn13:
            return "edition_isbn_" + self.isbn13
        return stable_id("edition", self.title, self.authors[0] if self.authors else "", self.publisher or "", self.published or "", self.language or "und", self.format or "")

    @property
    def quality(self) -> str:
        return quality_tier(self)

    def json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))


def quality_tier(record: CanonicalRecord) -> str:
    if record.isbn13 and record.authors and (record.publisher or record.published):
        return "A"
    if record.authors:
        return "B"
    return "C"
