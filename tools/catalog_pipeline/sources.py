from __future__ import annotations

import csv
import gzip
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .models import CanonicalRecord, clean


def _id(value) -> str:
    if isinstance(value, dict): value = value.get("key") or value.get("value")
    return str(value or "").rstrip("/").split("/")[-1]


def _names(values) -> list[str]:
    result=[]
    for value in values or []:
        if isinstance(value, dict): value=value.get("name") or value.get("literal") or value.get("family")
        if clean(value): result.append(clean(value))
    return result


def openlibrary(record: dict, author_names: dict[str, str] | None = None) -> CanonicalRecord | None:
    kind=_id(record.get("type")); key=_id(record.get("key")); title=clean(record.get("title"))
    if kind not in ("edition","work","") or not key or not title: return None
    author_names=author_names or {}; authors=[]
    for item in record.get("authors", []):
        author_id=_id(item); authors.append(author_names.get(author_id, author_id) if author_id else "")
    if kind=="work":
        ids={"olid":[key]}; description=record.get("description"); description=description.get("value") if isinstance(description,dict) else description
        return CanonicalRecord("openlibrary",key,title,kind="work",authors=authors,description=description,subjects=_names(record.get("subjects")),identifiers=ids,cover_url=(f"https://covers.openlibrary.org/b/id/{record['covers'][0]}-L.jpg" if record.get("covers") else None),work_hint=key,published=record.get("first_publish_date")).normalized()
    works=record.get("works") or []
    ids={"isbn": list(record.get("isbn_13", []))+list(record.get("isbn_10", [])), "lccn": list(record.get("lccn", [])), "olid":[key]}
    return CanonicalRecord("openlibrary",key,title,authors=authors,publisher=next(iter(record.get("publishers") or []),None),published=record.get("publish_date"),language=_id(next(iter(record.get("languages") or []),None)),format=record.get("physical_format"),subjects=_names(record.get("subjects")),identifiers=ids,cover_url=(f"https://covers.openlibrary.org/b/id/{record['covers'][0]}-L.jpg" if record.get("covers") else None),work_hint=_id(works[0]) if works else None).normalized()


def read_openlibrary_authors(path: Path):
    opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"rt",encoding="utf-8",errors="replace") as stream:
        for line in stream:
            columns=line.rstrip("\n").split("\t",4)
            if len(columns)!=5: continue
            try: record=json.loads(columns[4])
            except json.JSONDecodeError: continue
            key=_id(record.get("key")); name=clean(record.get("name"))
            if key and name: yield key,name


def crossref(item: dict) -> CanonicalRecord | None:
    allowed={"book","monograph","edited-book","reference-book","book-set","book-series"}
    if item.get("type") not in allowed: return None
    title=clean(next(iter(item.get("title") or []),None)); doi=clean(item.get("DOI"))
    if not title or not doi: return None
    authors=[]
    for person in item.get("author",[]):
        name=clean(" ".join(filter(None,[person.get("given"),person.get("family")])))
        if name: authors.append(name)
    return CanonicalRecord("crossref",doi,title,authors=authors,publisher=item.get("publisher"),published=_date_parts(item),language=item.get("language"),format=item.get("type"),description=item.get("abstract"),subjects=_names(item.get("subject")),identifiers={"doi":[doi],"isbn":item.get("ISBN",[])},access_url=item.get("URL")).normalized()


def datacite(item: dict) -> CanonicalRecord | None:
    attrs=item.get("attributes",item); types=attrs.get("types") or {}
    if str(types.get("resourceTypeGeneral","")).casefold() != "book": return None
    title=clean(next((v.get("title") for v in attrs.get("titles",[]) if v.get("title")),None)); source_id=clean(attrs.get("doi") or item.get("id"))
    if not title or not source_id: return None
    authors=[]
    for person in attrs.get("creators",[]):
        name=clean(person.get("name") or " ".join(filter(None,[person.get("givenName"),person.get("familyName")])))
        if name: authors.append(name)
    ids={"doi":[source_id],"isbn":[v.get("identifier") for v in attrs.get("identifiers",[]) if str(v.get("identifierType","")).casefold()=="isbn"]}
    descriptions=[v.get("description") for v in attrs.get("descriptions",[]) if v.get("description")]
    return CanonicalRecord("datacite",source_id,title,authors=authors,publisher=attrs.get("publisher"),published=str(attrs.get("publicationYear") or "") or None,language=attrs.get("language"),format=types.get("resourceType"),description=next(iter(descriptions),None),subjects=_names(attrs.get("subjects")),identifiers=ids,access_url=attrs.get("url")).normalized()


def doab(metadata: dict) -> CanonicalRecord | None:
    title=clean(next(iter(metadata.get("dc.title",[])),None)); source_id=clean(next(iter(metadata.get("dc.identifier.uri",[]) or metadata.get("dc.identifier",[])),None))
    if not title or not source_id: return None
    identifiers=metadata.get("dc.identifier.isbn",[])+[v for v in metadata.get("dc.identifier",[]) if "isbn" in v.casefold()]
    return CanonicalRecord("doab",source_id,title,authors=metadata.get("dc.contributor.author",[]) or metadata.get("dc.creator",[]),publisher=next(iter(metadata.get("dc.publisher",[])),None),published=next(iter(metadata.get("dc.date.issued",[])),None),language=next(iter(metadata.get("dc.language",[])),None),description=next(iter(metadata.get("dc.description.abstract",[])),None),subjects=metadata.get("dc.subject",[]),identifiers={"isbn":identifiers,"doi":metadata.get("dc.identifier.doi",[])},access_url=source_id).normalized()


def doab_oai(item: dict) -> CanonicalRecord | None:
    metadata=item.get("metadata",{}); source_id=item.get("source_id")
    mapped={
        "dc.title":metadata.get("title",[]),"dc.creator":metadata.get("creator",[]),"dc.publisher":metadata.get("publisher",[]),
        "dc.date.issued":metadata.get("date",[]),"dc.language":metadata.get("language",[]),"dc.subject":metadata.get("subject",[]),
        "dc.description.abstract":metadata.get("description",[]),"dc.identifier":metadata.get("identifier",[]),"dc.identifier.uri":[source_id] if source_id else [],
        "dc.identifier.isbn":[value for value in metadata.get("identifier",[]) if "isbn" in value.casefold() or any(ch.isdigit() for ch in value)],
    }
    return doab(mapped)


def gutenberg(row: dict) -> CanonicalRecord | None:
    source_id=clean(row.get("Text#") or row.get("id") or row.get("ebook_id")); title=clean(row.get("Title") or row.get("title"))
    if not source_id or not title: return None
    authors=[v.strip() for v in str(row.get("Authors") or row.get("Author") or "").split(";") if v.strip()]
    return CanonicalRecord("gutenberg",source_id,title,authors=authors,language=clean(row.get("Language") or row.get("Languages")),subjects=[v.strip() for v in str(row.get("Subjects") or "").split(";") if v.strip()],identifiers={"gutenberg":[source_id]},access_url=f"https://www.gutenberg.org/ebooks/{source_id}").normalized()


def loc(record) -> CanonicalRecord | None:
    title=clean(record.title()); source_id=clean(record["001"].value() if record["001"] else None)
    if not title or not source_id: return None
    authors=[]
    for tag in ("100","110","111","700","710","711"):
        for field in record.get_fields(tag):
            name=clean(field.get("a"));
            if name: authors.append(name.rstrip(" ,/"))
    isbns=[field.get("a") for field in record.get_fields("020") if field.get("a")]
    publishers=[]; dates=[]
    for field in record.get_fields("260","264"):
        if field.get("b"): publishers.append(field.get("b").rstrip(" ,"))
        if field.get("c"): dates.append(field.get("c").strip(" .[]c"))
    subjects=[" -- ".join(field.get_subfields("a","x","y","z")) for field in record.get_fields("600","610","650","651")]
    return CanonicalRecord("loc",source_id,title,authors=authors,publisher=next(iter(publishers),None),published=next(iter(dates),None),language=(record["008"].data[35:38] if record["008"] and len(record["008"].data)>=38 else None),identifiers={"isbn":isbns,"lccn":[source_id]},subjects=subjects).normalized()


def _date_parts(item):
    for key in ("published-print","published-online","issued","created"):
        parts=((item.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]: return "-".join(str(v) for v in parts[0])
    return None


def read_openlibrary(path: Path, author_names=None):
    opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"rt",encoding="utf-8",errors="replace") as stream:
        for line in stream:
            columns=line.rstrip("\n").split("\t",4)
            if len(columns)!=5: continue
            try: record=json.loads(columns[4])
            except json.JSONDecodeError: continue
            if parsed:=openlibrary(record,author_names): yield parsed


def read_jsonl(path: Path, parser):
    opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"rt",encoding="utf-8",errors="replace") as stream:
        for line in stream:
            try: item=json.loads(line)
            except json.JSONDecodeError: continue
            if parsed:=parser(item): yield parsed


def read_csv(path: Path, parser=gutenberg):
    with path.open(encoding="utf-8-sig",errors="replace",newline="") as stream:
        for row in csv.DictReader(stream):
            if parsed:=parser(row): yield parsed


def read_marc(path: Path):
    from pymarc import MARCReader
    opener=gzip.open if path.suffix==".gz" else open
    with opener(path,"rb") as stream:
        for record in MARCReader(stream,to_unicode=True,force_utf8=True,utf8_handling="replace",permissive=True):
            if record and (parsed:=loc(record)): yield parsed
