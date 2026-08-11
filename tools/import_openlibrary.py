#!/usr/bin/env python3
"""Convert Open Library monthly TSV dumps into idempotent D1 SQL batches.

The importer intentionally streams gzip input and writes SQL without retaining the
dump in memory. Start with --limit, then remove it for a full production import.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path


def sql(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''").replace("\x00", "") + "'"


def key_id(value):
    return str(value or "").rstrip("/").split("/")[-1]


def ref_id(value):
    if isinstance(value, dict):
        value = value.get("key") or value.get("value")
    return key_id(value)


def first(value, default=None):
    return value[0] if isinstance(value, list) and value else default


def year(value):
    match = re.search(r"(?:1[0-9]{3}|20[0-9]{2})", str(value or ""))
    return int(match.group()) if match else None


def read_dump(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            columns = line.rstrip("\n").split("\t", 4)
            if len(columns) == 5:
                try:
                    yield json.loads(columns[4])
                except json.JSONDecodeError:
                    continue


def work_sql(record):
    work_id = key_id(record.get("key"))
    title = str(record.get("title") or "").strip()
    if not work_id or not title:
        return []
    authors = [ref_id(item.get("author", item)) for item in record.get("authors", [])]
    author = ", ".join(filter(None, authors)) or "Unknown author"
    subjects = [str(item)[:160] for item in record.get("subjects", [])[:30]]
    cover = first(record.get("covers"))
    updated = str(record.get("last_modified", {}).get("value") or "1970-01-01T00:00:00Z")
    values = [work_id, title, author, year(record.get("first_publish_date")), cover, json.dumps(subjects, ensure_ascii=False), "openlibrary", updated]
    search = " ".join(subjects)
    return [
        "INSERT INTO catalog_works(id,title,author,first_publish_year,cover_id,subjects_json,source,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,unixepoch(%s)) ON CONFLICT(id) DO UPDATE SET title=excluded.title,first_publish_year=excluded.first_publish_year,cover_id=excluded.cover_id,subjects_json=excluded.subjects_json,updated_at=excluded.updated_at;" % tuple(map(sql, values)),
        f"DELETE FROM catalog_works_fts WHERE id={sql(work_id)};",
        "INSERT INTO catalog_works_fts(id,title,author,subjects) VALUES(%s,%s,%s,%s);" % tuple(map(sql, [work_id, title, author, search])),
    ]


def edition_sql(record):
    edition_id = key_id(record.get("key"))
    work_id = ref_id(first(record.get("works")))
    title = str(record.get("title") or "").strip()
    if not edition_id or not work_id or not title:
        return []
    publishers = record.get("publishers") or []
    languages = record.get("languages") or []
    values = [edition_id, work_id, title, first(publishers), record.get("publish_date"), ref_id(first(languages)), first(record.get("physical_format")) if isinstance(record.get("physical_format"), list) else record.get("physical_format"), first(record.get("covers")), "openlibrary"]
    statements = ["INSERT INTO catalog_editions(id,work_id,title,publisher,publish_date,language,format,cover_id,source) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET work_id=excluded.work_id,title=excluded.title,publisher=excluded.publisher,publish_date=excluded.publish_date,language=excluded.language,format=excluded.format,cover_id=excluded.cover_id;" % tuple(map(sql, values))]
    for scheme in ("isbn_10", "isbn_13"):
        for identifier in record.get(scheme, [])[:10]:
            normalized = re.sub(r"[^0-9X]", "", str(identifier).upper())
            if normalized:
                statements.append("INSERT OR IGNORE INTO catalog_identifiers(scheme,value,edition_id) VALUES(%s,%s,%s);" % tuple(map(sql, [scheme, normalized, edition_id])))
    return statements


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("dump", type=Path)
    parser.add_argument("--type", choices=("works", "editions"), required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    output = args.output.open("w", encoding="utf-8") if args.output else sys.stdout
    convert = work_sql if args.type == "works" else edition_sql
    count = 0
    try:
        output.write("PRAGMA foreign_keys=OFF;\n")
        for record in read_dump(args.dump):
            statements = convert(record)
            if not statements:
                continue
            output.write("\n".join(statements) + "\n")
            count += 1
            if args.limit and count >= args.limit:
                break
    finally:
        if output is not sys.stdout:
            output.close()
    print(f"converted {count} {args.type} records", file=sys.stderr)


if __name__ == "__main__":
    main()
