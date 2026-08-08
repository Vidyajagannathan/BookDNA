import secrets
import time
from workers import DurableObject
from security.tokens import hash_password, verify_password

class IdentityDO(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env); self.sql = ctx.storage.sql
        self.sql.exec("""CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT NOT NULL,username_normalized TEXT UNIQUE NOT NULL,email_normalized TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at INTEGER NOT NULL,account_status TEXT NOT NULL DEFAULT 'ACTIVE'); CREATE TABLE IF NOT EXISTS refresh_sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,token_hash TEXT NOT NULL,expires_at INTEGER NOT NULL,revoked_at INTEGER);""")

    async def register(self, username, email, password):
        uname=username.strip(); un=uname.casefold(); em=email.strip().casefold()
        if len(uname)<3 or len(password)<8 or "@" not in em: return {"error":"Invalid registration details"}
        if list(self.sql.exec("SELECT id FROM users WHERE username_normalized=? OR email_normalized=?",un,em)): return {"error":"Username or email is already in use"}
        uid=f"usr_{secrets.token_hex(10)}"; now=int(time.time())
        self.sql.exec("INSERT INTO users VALUES(?,?,?,?,?,?,?)",uid,uname,un,em,hash_password(password),now,"ACTIVE")
        return {"id":uid,"username":uname}

    async def authenticate(self, identifier, password):
        value=identifier.strip().casefold(); rows=list(self.sql.exec("SELECT id,username,password_hash FROM users WHERE username_normalized=? OR email_normalized=? LIMIT 1",value,value))
        if not rows or not verify_password(password, rows[0].password_hash): return {"error":"Invalid username/email or password"}
        return {"id":rows[0].id,"username":rows[0].username}

    async def username_for(self, user_id):
        rows=list(self.sql.exec("SELECT username FROM users WHERE id=?",user_id)); return rows[0].username if rows else None

