import json
import time
from workers import DurableObject
from dna.scoring import Signal, contribution, calibrated_display_score
from dna.mappings import classify_book


class UserDO(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.sql = ctx.storage.sql
        self.sql.exec("""CREATE TABLE IF NOT EXISTS profile(user_id TEXT PRIMARY KEY,username TEXT NOT NULL,created_at INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS library_entries(book_id TEXT PRIMARY KEY,book_json TEXT NOT NULL,status TEXT NOT NULL,rating REAL,is_favourite INTEGER NOT NULL DEFAULT 0,traits_json TEXT NOT NULL DEFAULT '{}',contribution_json TEXT NOT NULL DEFAULT '{}',updated_at INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS dna_scores(trait_id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,evidence REAL NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS dna_negative_signals(trait_id TEXT PRIMARY KEY,evidence REAL NOT NULL DEFAULT 0);""")
        columns = {row.name for row in self.sql.exec("PRAGMA table_info(library_entries)")}
        if "dnf_reason" not in columns:
            self.sql.exec("ALTER TABLE library_entries ADD COLUMN dnf_reason TEXT")
        if "private_note" not in columns:
            self.sql.exec("ALTER TABLE library_entries ADD COLUMN private_note TEXT")

    async def initialize(self, user_id, username):
        self.sql.exec("INSERT OR IGNORE INTO profile VALUES(?,?,?)", user_id, username, int(time.time()))
        return True

    async def library(self):
        return [dict(json.loads(row.book_json), status=row.status, rating=row.rating, favourite=bool(row.is_favourite), dnf_reason=row.dnf_reason, private_note=row.private_note) for row in self.sql.exec("SELECT * FROM library_entries ORDER BY updated_at DESC LIMIT 500")]

    async def upsert_book(self, book, status, rating, favourite, traits, dnf_reason=None, private_note=None):
        if status not in ("READ", "CURRENTLY_READING", "WANT_TO_READ", "DNF"):
            return {"error": "Invalid reading status"}
        prior = list(self.sql.exec("SELECT contribution_json,traits_json,status FROM library_entries WHERE book_id=?", book["id"]))
        if prior:
            for trait_id, value in json.loads(prior[0].contribution_json).items():
                self.sql.exec("UPDATE dna_scores SET evidence=MAX(0,evidence-?) WHERE trait_id=?", value, trait_id)
            if prior[0].status=="DNF":
                for trait in json.loads(prior[0].traits_json): self.sql.exec("UPDATE dna_negative_signals SET evidence=MAX(0,evidence-?) WHERE trait_id=?",trait["weight"],trait["id"])
        trait_weights = {trait["id"]: trait["weight"] for trait in traits}
        new = contribution(Signal(status, rating, favourite), trait_weights)
        for trait in traits:
            value = new.get(trait["id"], 0)
            self.sql.exec("INSERT INTO dna_scores(trait_id,name,category,evidence) VALUES(?,?,?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence", trait["id"], trait["name"], trait["category"], value)
            if status == "DNF":
                self.sql.exec("INSERT INTO dna_negative_signals VALUES(?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence", trait["id"], trait["weight"])
        reason = (str(dnf_reason).strip()[:500] or None) if status == "DNF" and dnf_reason else None
        note=(str(private_note).strip()[:2000] or None) if private_note else None
        self.sql.exec("INSERT INTO library_entries(book_id,book_json,status,rating,is_favourite,traits_json,contribution_json,updated_at,dnf_reason,private_note) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(book_id) DO UPDATE SET book_json=excluded.book_json,status=excluded.status,rating=excluded.rating,is_favourite=excluded.is_favourite,traits_json=excluded.traits_json,contribution_json=excluded.contribution_json,updated_at=excluded.updated_at,dnf_reason=excluded.dnf_reason,private_note=excluded.private_note", book["id"], json.dumps(book), status, rating, 1 if favourite else 0, json.dumps(traits), json.dumps(new), int(time.time()), reason, note)
        return dict(book, status=status, rating=rating, favourite=favourite, dnf_reason=reason, private_note=note)

    async def dna(self):
        self._rebuild_dna()
        rows = list(self.sql.exec("SELECT * FROM dna_scores WHERE evidence>0 ORDER BY evidence DESC"))
        total = sum(row.evidence for row in rows)
        entries=list(self.sql.exec("SELECT book_id,book_json,status,rating,is_favourite,traits_json,contribution_json FROM library_entries")); shaping=[entry for entry in entries if json.loads(entry.contribution_json)]
        traits=[]
        for row in rows:
            supporting=[]
            for entry in shaping:
                amount=json.loads(entry.contribution_json).get(row.trait_id,0)
                if amount>0:
                    book=json.loads(entry.book_json); supporting.append({"id":book["id"],"title":book["title"],"author":book.get("author"),"rating":entry.rating,"favourite":bool(entry.is_favourite),"evidence":round(amount,2)})
            supporting.sort(key=lambda item:item["evidence"],reverse=True)
            score=calibrated_display_score(row.evidence,total,len(supporting))
            traits.append({"id":row.trait_id,"name":row.name,"category":row.category,"score":score,"confidence":round(row.evidence/(row.evidence+1.8),2),"supporting_books":supporting[:6]})
        completed_entries=[entry for entry in entries if entry.status=="READ"]; completed=len(completed_entries); total_books=len(entries); completed_included=sum(bool(json.loads(entry.contribution_json)) for entry in completed_entries); rated=sum(entry.rating is not None for entry in shaping); categories=len({row.category for row in rows}); breadth=min(1,len(rows)/8); depth=min(1,len(shaping)/10); quality=min(1,(completed_included+rated*.5)/10); profile_confidence=round(100*(.35*breadth+.4*depth+.25*quality)) if rows else 0
        label="Established" if profile_confidence>=75 else "Developing" if profile_confidence>=40 else "Early"
        classifications=[]
        for entry in completed_entries:
            book=json.loads(entry.book_json); classification=classify_book(book); included=bool(json.loads(entry.contribution_json))
            classifications.append({"id":book["id"],"title":book.get("title","Untitled"),"author":book.get("author"),"included":included,"state":"included" if included else "needs_classification","reason":self._classification_reason(classification,included),"reading_type":classification["reading_type"],"classification_source":classification["source"],"traits":[trait["name"] for trait in classification["traits"]]})
        classifications.sort(key=lambda item:(not item["included"],item["title"].casefold()))
        return {"evidence":round(total,1),"profile_confidence":profile_confidence,"confidence_label":label,"books_shaping":len(shaping),"completed_books":completed,"total_books":total_books,"completion_rate":round(100*completed/total_books) if total_books else 0,"active_traits":len(rows),"active_categories":categories,"completed_classifications":classifications,"traits":traits}

    def _classification_reason(self,classification,included):
        if not included: return "No recognised catalogue subjects or reliable title match yet."
        if classification["source"]=="title_author_fallback": return "Included using a conservative title and author match."
        return "Included using catalogue subjects."

    def _rebuild_dna(self):
        """Reclassify existing entries so mapping improvements apply without re-saving books."""
        entries=list(self.sql.exec("SELECT book_id,book_json,status,rating,is_favourite FROM library_entries"))
        self.sql.exec("DELETE FROM dna_scores; DELETE FROM dna_negative_signals;")
        for entry in entries:
            book=json.loads(entry.book_json); traits=classify_book(book)["traits"]; weights={trait["id"]:trait["weight"] for trait in traits}; new=contribution(Signal(entry.status,entry.rating,bool(entry.is_favourite)),weights)
            self.sql.exec("UPDATE library_entries SET traits_json=?,contribution_json=? WHERE book_id=?",json.dumps(traits),json.dumps(new),entry.book_id)
            for trait in traits:
                value=new.get(trait["id"],0)
                if value>0: self.sql.exec("INSERT INTO dna_scores(trait_id,name,category,evidence) VALUES(?,?,?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence",trait["id"],trait["name"],trait["category"],value)
                if entry.status=="DNF": self.sql.exec("INSERT INTO dna_negative_signals VALUES(?,?) ON CONFLICT(trait_id) DO UPDATE SET evidence=evidence+excluded.evidence",trait["id"],trait["weight"])

    async def remove_book(self,book_id):
        prior=list(self.sql.exec("SELECT contribution_json,traits_json,status FROM library_entries WHERE book_id=?",book_id))
        if not prior: return {"error":"Book not found"}
        for trait_id,value in json.loads(prior[0].contribution_json).items(): self.sql.exec("UPDATE dna_scores SET evidence=MAX(0,evidence-?) WHERE trait_id=?",value,trait_id)
        if prior[0].status=="DNF":
            for trait in json.loads(prior[0].traits_json): self.sql.exec("UPDATE dna_negative_signals SET evidence=MAX(0,evidence-?) WHERE trait_id=?",trait["weight"],trait["id"])
        self.sql.exec("DELETE FROM library_entries WHERE book_id=?",book_id); self.sql.exec("DELETE FROM dna_scores WHERE evidence<=0; DELETE FROM dna_negative_signals WHERE evidence<=0;")
        return {"ok":True}

    async def delete_account_data(self):
        self.sql.exec("DELETE FROM library_entries; DELETE FROM dna_scores; DELETE FROM dna_negative_signals; DELETE FROM profile;")
        return True
