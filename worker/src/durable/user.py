import json
import time
from workers import DurableObject
from dna.scoring import Signal, contribution, display_score

class UserDO(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx,env); self.sql=ctx.storage.sql
        self.sql.exec("""CREATE TABLE IF NOT EXISTS profile(user_id TEXT PRIMARY KEY,username TEXT NOT NULL,created_at INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS library_entries(book_id TEXT PRIMARY KEY,book_json TEXT NOT NULL,status TEXT NOT NULL,rating REAL,is_favourite INTEGER NOT NULL DEFAULT 0,traits_json TEXT NOT NULL DEFAULT '{}',contribution_json TEXT NOT NULL DEFAULT '{}',updated_at INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS dna_scores(trait_id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,evidence REAL NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS dna_negative_signals(trait_id TEXT PRIMARY KEY,evidence REAL NOT NULL DEFAULT 0);""")

    async def initialize(self,user_id,username):
        self.sql.exec("INSERT OR IGNORE INTO profile VALUES(?,?,?)",user_id,username,int(time.time())); return True

    async def library(self):
        return [dict(json.loads(r.book_json),status=r.status,rating=r.rating,favourite=bool(r.is_favourite)) for r in self.sql.exec("SELECT * FROM library_entries ORDER BY updated_at DESC LIMIT 100")]

    async def upsert_book(self, book, status, rating, favourite, traits):
        if status not in ("READ","CURRENTLY_READING","WANT_TO_READ","DNF"): return {"error":"Invalid reading status"}
        prior=list(self.sql.exec("SELECT contribution_json,traits_json,status FROM library_entries WHERE book_id=?",book["id"]))
        if prior:
            old=json.loads(prior[0].contribution_json)
            for trait_id,value in old.items(): self.sql.exec("UPDATE dna_scores SET evidence=MAX(0,evidence-?) WHERE trait_id=?",value,trait_id)
        trait_weights={t["id"]:t["weight"] for t in traits}; new=contribution(Signal(status,rating,favourite),trait_weights)
        for trait in traits:
            value=new.get(trait["id"],0)
            self.sql.exec("INSERT INTO dna_scores(trait_id,name,category,evidence) VALUES(?,?,?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence",trait["id"],trait["name"],trait["category"],value)
            if status=="DNF": self.sql.exec("INSERT INTO dna_negative_signals VALUES(?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence",trait["id"],trait["weight"])
        self.sql.exec("INSERT INTO library_entries VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(book_id) DO UPDATE SET book_json=excluded.book_json,status=excluded.status,rating=excluded.rating,is_favourite=excluded.is_favourite,traits_json=excluded.traits_json,contribution_json=excluded.contribution_json,updated_at=excluded.updated_at",book["id"],json.dumps(book),status,rating,1 if favourite else 0,json.dumps(traits),json.dumps(new),int(time.time()))
        return dict(book,status=status,rating=rating,favourite=favourite)

    async def dna(self):
        rows=list(self.sql.exec("SELECT * FROM dna_scores WHERE evidence>0 ORDER BY evidence DESC")); total=sum(r.evidence for r in rows)
        return {"evidence":round(total,1),"traits":[{"id":r.trait_id,"name":r.name,"category":r.category,"score":display_score(r.evidence,total),"confidence":round(r.evidence/(r.evidence+1.8),2)} for r in rows]}

