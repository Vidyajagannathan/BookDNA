from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

import duckdb

from .models import CanonicalRecord, SOURCE_PRIORITY

LOCAL_CAP = 140 * 1024**3
ARCHIVE_CAP = 8 * 1024**3
D1_TOTAL_CAP = 4 * 1024**3
D1_SHARD_CAP = 400 * 1024**2

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_claims(
 source VARCHAR NOT NULL, source_id VARCHAR NOT NULL, edition_id VARCHAR NOT NULL,
 work_id VARCHAR NOT NULL, quality VARCHAR NOT NULL, payload JSON NOT NULL,
 ingested_at TIMESTAMP NOT NULL, PRIMARY KEY(source,source_id)
);
CREATE TABLE IF NOT EXISTS works(
 id VARCHAR PRIMARY KEY, title VARCHAR NOT NULL, primary_author VARCHAR,
 language VARCHAR, first_published VARCHAR, quality VARCHAR NOT NULL,
 source_priority INTEGER NOT NULL, edition_count BIGINT NOT NULL DEFAULT 0,
 sources JSON NOT NULL, updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS editions(
 id VARCHAR PRIMARY KEY, work_id VARCHAR NOT NULL, title VARCHAR NOT NULL,
 primary_author VARCHAR, publisher VARCHAR, published VARCHAR, language VARCHAR,
 format VARCHAR, quality VARCHAR NOT NULL, source_priority INTEGER NOT NULL,
 payload JSON NOT NULL, updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS identifiers(
 scheme VARCHAR NOT NULL, value VARCHAR NOT NULL, edition_id VARCHAR NOT NULL,
 source VARCHAR NOT NULL, PRIMARY KEY(scheme,value,edition_id,source)
);
CREATE TABLE IF NOT EXISTS checkpoints(
 source VARCHAR PRIMARY KEY, cursor VARCHAR, seen BIGINT NOT NULL DEFAULT 0,
 accepted BIGINT NOT NULL DEFAULT 0, rejected BIGINT NOT NULL DEFAULT 0,
 updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS rejections(
 source VARCHAR NOT NULL, source_id VARCHAR, reason VARCHAR NOT NULL,
 payload JSON, rejected_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS openlibrary_authors(
 id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL
);
"""


def directory_size(path: Path) -> int:
    if not path.exists(): return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def sha256_file(path: Path) -> str:
    digest=sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


class CatalogPipeline:
    def __init__(self, workspace: Path, *, local_cap: int = LOCAL_CAP):
        self.workspace=workspace.resolve(); self.workspace.mkdir(parents=True,exist_ok=True)
        self.local_cap=local_cap; self.database_path=self.workspace/"catalog.duckdb"
        self.db=duckdb.connect(str(self.database_path)); self.db.execute(SCHEMA)

    def close(self): self.db.close()

    def check_local_capacity(self):
        used=directory_size(self.workspace); free=shutil.disk_usage(self.workspace).free
        if used>=self.local_cap: raise RuntimeError(f"catalog workspace cap reached: {used} >= {self.local_cap}")
        if free<2*1024**3: raise RuntimeError("less than 2 GiB free; refusing catalog write")

    def checkpoint(self, source: str) -> dict:
        row=self.db.execute("SELECT cursor,seen,accepted,rejected FROM checkpoints WHERE source=?",[source]).fetchone()
        return dict(zip(("cursor","seen","accepted","rejected"),row)) if row else {"cursor":None,"seen":0,"accepted":0,"rejected":0}

    def ingest(self, source: str, records, *, limit: int | None = None, cursor: str | None = None, batch_size: int = 1000) -> dict:
        state=self.checkpoint(source); seen=accepted=rejected=0; batch=[]
        for record in records:
            seen+=1
            if not record or not record.source_id or not record.title:
                rejected+=1; continue
            batch.append(record.normalized())
            if len(batch)>=batch_size:
                accepted+=self._write_batch(batch); batch=[]; self.check_local_capacity()
            if limit and seen>=limit: break
        if batch: accepted+=self._write_batch(batch)
        self.db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,current_timestamp) ON CONFLICT(source) DO UPDATE SET cursor=excluded.cursor,seen=checkpoints.seen+excluded.seen,accepted=checkpoints.accepted+excluded.accepted,rejected=checkpoints.rejected+excluded.rejected,updated_at=excluded.updated_at",[source,cursor,seen,accepted,rejected])
        self._refresh_counts(); self.write_manifest()
        return {"source":source,"seen":seen,"accepted":accepted,"rejected":rejected,"checkpoint":cursor}

    def ingest_openlibrary_authors(self, authors, *, limit: int | None = None, batch_size: int = 10000):
        seen=0; batch=[]
        for author in authors:
            batch.append(author); seen+=1
            if len(batch)>=batch_size:
                self.db.executemany("INSERT INTO openlibrary_authors VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",batch); batch=[]; self.check_local_capacity()
            if limit and seen>=limit: break
        if batch: self.db.executemany("INSERT INTO openlibrary_authors VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",batch)
        return {"source":"openlibrary-authors","accepted":seen}

    def openlibrary_author_map(self):
        return dict(self.db.execute("SELECT id,name FROM openlibrary_authors").fetchall())

    def reject(self, source: str, source_id: str | None, reason: str, payload=None):
        self.db.execute("INSERT INTO rejections VALUES(?,?,?,?,current_timestamp)",[source,source_id,reason,json.dumps(payload,ensure_ascii=False) if payload is not None else None])

    def _write_batch(self, records: list[CanonicalRecord]) -> int:
        now=datetime.now(timezone.utc); self.db.execute("BEGIN")
        try:
            for record in records:
                priority=SOURCE_PRIORITY.get(record.source,0); author=record.authors[0] if record.authors else None; payload=record.json()
                self.db.execute("INSERT INTO source_claims VALUES(?,?,?,?,?,?,?) ON CONFLICT(source,source_id) DO UPDATE SET edition_id=excluded.edition_id,work_id=excluded.work_id,quality=excluded.quality,payload=excluded.payload,ingested_at=excluded.ingested_at",[record.source,record.source_id,record.edition_id if record.kind=="edition" else "",record.work_id,record.quality,payload,now])
                if record.kind=="work":
                    existing=self.db.execute("SELECT source_priority,sources FROM works WHERE id=?",[record.work_id]).fetchone(); sources=set(json.loads(existing[1])) if existing else set(); sources.add(record.source)
                    if not existing or priority>=existing[0]: self.db.execute("INSERT INTO works VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,primary_author=excluded.primary_author,language=excluded.language,first_published=excluded.first_published,quality=excluded.quality,source_priority=excluded.source_priority,sources=excluded.sources,updated_at=excluded.updated_at",[record.work_id,record.title,author,record.language,record.published,record.quality,priority,0,json.dumps(sorted(sources)),now])
                    else: self.db.execute("UPDATE works SET sources=?,updated_at=? WHERE id=?",[json.dumps(sorted(sources)),now,record.work_id])
                    continue
                current=self.db.execute("SELECT source_priority FROM editions WHERE id=?",[record.edition_id]).fetchone()
                if not current or priority>=current[0]:
                    self.db.execute("INSERT INTO editions VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET work_id=excluded.work_id,title=excluded.title,primary_author=excluded.primary_author,publisher=excluded.publisher,published=excluded.published,language=excluded.language,format=excluded.format,quality=excluded.quality,source_priority=excluded.source_priority,payload=excluded.payload,updated_at=excluded.updated_at",[record.edition_id,record.work_id,record.title,author,record.publisher,record.published,record.language,record.format,record.quality,priority,payload,now])
                existing=self.db.execute("SELECT source_priority,sources FROM works WHERE id=?",[record.work_id]).fetchone(); sources=set(json.loads(existing[1])) if existing else set(); sources.add(record.source)
                if not existing or priority>=existing[0]:
                    self.db.execute("INSERT INTO works VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,primary_author=excluded.primary_author,language=excluded.language,first_published=excluded.first_published,quality=excluded.quality,source_priority=excluded.source_priority,sources=excluded.sources,updated_at=excluded.updated_at",[record.work_id,record.title,author,record.language,record.published,record.quality,priority,0,json.dumps(sorted(sources)),now])
                else: self.db.execute("UPDATE works SET sources=?,updated_at=? WHERE id=?",[json.dumps(sorted(sources)),now,record.work_id])
                for scheme,values in record.identifiers.items():
                    for value in values: self.db.execute("INSERT OR IGNORE INTO identifiers VALUES(?,?,?,?)",[scheme,value,record.edition_id,record.source])
            self.db.execute("COMMIT"); return len(records)
        except Exception:
            self.db.execute("ROLLBACK"); raise

    def _refresh_counts(self):
        self.db.execute("UPDATE works SET edition_count=x.count FROM (SELECT work_id,count(*) count FROM editions GROUP BY work_id) x WHERE works.id=x.work_id")

    def report(self) -> dict:
        counts={table:self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("source_claims","works","editions","identifiers","rejections")}
        quality=dict(self.db.execute("SELECT quality,count(*) FROM editions GROUP BY quality ORDER BY quality").fetchall())
        sources={row[0]:{"seen":row[1],"accepted":row[2],"rejected":row[3]} for row in self.db.execute("SELECT source,seen,accepted,rejected FROM checkpoints ORDER BY source").fetchall()}
        return {"generated_at":datetime.now(timezone.utc).isoformat(),"counts":counts,"quality":quality,"sources":sources,"workspace_bytes":directory_size(self.workspace),"caps":{"local_bytes":self.local_cap,"archive_bytes":ARCHIVE_CAP,"d1_total_bytes":D1_TOTAL_CAP,"d1_shard_bytes":D1_SHARD_CAP}}

    def write_manifest(self):
        path=self.workspace/"manifest.json"; temporary=path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report(),indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(temporary,path)

    def export_archive(self, output: Path, *, archive_cap: int = ARCHIVE_CAP) -> dict:
        output.mkdir(parents=True,exist_ok=True)
        for bucket in range(256):
            target=output/f"editions-{bucket:02x}.parquet"
            self.db.execute(f"COPY (SELECT * FROM editions WHERE substr(md5(id),1,2)='{bucket:02x}' ORDER BY id) TO ? (FORMAT parquet,COMPRESSION zstd)",[str(target)])
            if directory_size(output)>archive_cap: target.unlink(missing_ok=True); raise RuntimeError("archive cap reached before export completed")
        self.db.execute("COPY (SELECT scheme,value,edition_id FROM identifiers ORDER BY scheme,value) TO ? (FORMAT parquet,COMPRESSION zstd)",[str(output/"identifiers.parquet")])
        size=directory_size(output)
        if size>archive_cap: raise RuntimeError("archive export exceeds cap")
        manifest={"bytes":size,"files":[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in sorted(output.glob("*.parquet"))]}
        (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
        return manifest

    def export_d1(self, output: Path, *, shard_count: int = 8, shard_cap: int = D1_SHARD_CAP, incremental: bool = False):
        output.mkdir(parents=True,exist_ok=True); results=[]
        for shard in range(shard_count):
            target=output/f"search-{shard}.sql"; estimated=0; count=0
            with target.open("w",encoding="utf-8") as stream:
                stream.write("PRAGMA foreign_keys=OFF;\n")
                if not incremental:
                    stream.write("DELETE FROM search_works_fts;\nDELETE FROM search_works;\n")
                rows=self.db.execute("SELECT id,title,primary_author,language,first_published,quality,edition_count,sources FROM works WHERE hash(id)%?=? ORDER BY CASE quality WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END, edition_count DESC",[shard_count,shard]).fetchall()
                for row in rows:
                    values=[row[0],row[1],row[2],row[3],row[4],None,row[5],row[6],row[7],None]
                    estimate=sum(len(str(value or "")) for value in values)+300
                    if estimated+estimate>shard_cap: break
                    encoded=",".join(self._sql(value) for value in values)
                    stream.write(f"INSERT INTO search_works(id,title,author,language,published,format,quality,edition_count,sources_json,cover_url,updated_at) VALUES({encoded},unixepoch()) ON CONFLICT(id) DO UPDATE SET title=excluded.title,author=excluded.author,language=excluded.language,published=excluded.published,quality=excluded.quality,edition_count=excluded.edition_count,sources_json=excluded.sources_json,updated_at=excluded.updated_at;\n")
                    if incremental:
                        stream.write(f"DELETE FROM search_works_fts WHERE id={self._sql(row[0])};\n")
                    stream.write(f"INSERT INTO search_works_fts(id,title,author) VALUES({self._sql(row[0])},{self._sql(row[1])},{self._sql(row[2])});\n")
                    estimated+=estimate; count+=1
            results.append({"shard":shard,"records":count,"estimated_database_bytes":estimated,"sql_bytes":target.stat().st_size,"path":str(target)})
        (output/"manifest.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8"); return results

    def export_identifiers(self, target: Path, *, cap: int = D1_SHARD_CAP, incremental: bool = False):
        target.parent.mkdir(parents=True,exist_ok=True); estimated=0; count=0
        with target.open("w",encoding="utf-8") as stream:
            stream.write("PRAGMA foreign_keys=OFF;\n")
            if not incremental: stream.write("DELETE FROM catalog_identifiers;\n")
            rows=self.db.execute("SELECT i.scheme,i.value,i.edition_id,e.work_id,e.title,e.primary_author,e.published,e.language,e.format,e.payload FROM identifiers i JOIN editions e ON e.id=i.edition_id ORDER BY CASE e.quality WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END,i.scheme,i.value").fetchall()
            for row in rows:
                original=json.loads(row[9]); compact=json.dumps({"work_id":row[3],"title":row[4],"authors":[row[5]] if row[5] else [],"published":row[6],"language":row[7],"format":row[8],"cover_url":original.get("cover_url")},ensure_ascii=False,separators=(",",":"))
                values=[row[0],row[1],row[2],row[3],compact]; estimate=sum(len(str(value or "")) for value in values)+150
                if estimated+estimate>cap: break
                stream.write("INSERT OR IGNORE INTO catalog_identifiers VALUES("+",".join(self._sql(value) for value in values)+");\n")
                estimated+=estimate; count+=1
        return {"records":count,"estimated_database_bytes":estimated,"sql_bytes":target.stat().st_size,"path":str(target)}

    @staticmethod
    def _sql(value):
        if value is None: return "NULL"
        if isinstance(value,(int,float)): return str(value)
        return "'"+str(value).replace("'","''").replace("\x00","")+"'"
