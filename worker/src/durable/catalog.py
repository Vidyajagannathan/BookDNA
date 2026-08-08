import json
import time
from workers import DurableObject

class CatalogShardDO(DurableObject):
    def __init__(self,ctx,env):
        super().__init__(ctx,env); self.sql=ctx.storage.sql
        self.sql.exec("CREATE TABLE IF NOT EXISTS books(id TEXT PRIMARY KEY,data_json TEXT NOT NULL,traits_json TEXT NOT NULL,updated_at INTEGER NOT NULL)")
    async def put_book(self,book,traits):
        self.sql.exec("INSERT INTO books VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET data_json=excluded.data_json,traits_json=excluded.traits_json,updated_at=excluded.updated_at",book["id"],json.dumps(book),json.dumps(traits),int(time.time())); return True
    async def get_book(self,book_id):
        rows=list(self.sql.exec("SELECT data_json,traits_json FROM books WHERE id=?",book_id)); return {"book":json.loads(rows[0].data_json),"traits":json.loads(rows[0].traits_json)} if rows else None

