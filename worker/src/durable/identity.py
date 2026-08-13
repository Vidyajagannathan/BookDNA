import secrets
import time
import hashlib
from workers import DurableObject
from security.tokens import hash_password, verify_password


class IdentityDO(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.sql = ctx.storage.sql
        self.sql.exec("""CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT NOT NULL,username_normalized TEXT UNIQUE NOT NULL,email_normalized TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at INTEGER NOT NULL,account_status TEXT NOT NULL DEFAULT 'ACTIVE'); CREATE TABLE IF NOT EXISTS refresh_sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,token_hash TEXT NOT NULL,expires_at INTEGER NOT NULL,revoked_at INTEGER); CREATE TABLE IF NOT EXISTS auth_attempts(bucket TEXT NOT NULL,attempted_at INTEGER NOT NULL); CREATE INDEX IF NOT EXISTS auth_attempts_bucket_time ON auth_attempts(bucket,attempted_at); CREATE TABLE IF NOT EXISTS product_events(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,event_type TEXT NOT NULL,created_at INTEGER NOT NULL); CREATE INDEX IF NOT EXISTS product_events_type_time ON product_events(event_type,created_at);""")
        columns = {row.name for row in self.sql.exec("PRAGMA table_info(users)")}
        if "last_login_at" not in columns:
            self.sql.exec("ALTER TABLE users ADD COLUMN last_login_at INTEGER")
        if "last_activity_at" not in columns:
            self.sql.exec("ALTER TABLE users ADD COLUMN last_activity_at INTEGER")
        additions={"display_name":"TEXT","timezone":"TEXT NOT NULL DEFAULT 'UTC'","date_format":"TEXT NOT NULL DEFAULT 'DD/MM/YYYY'","language":"TEXT NOT NULL DEFAULT 'en'","avatar":"TEXT NOT NULL DEFAULT 'forest'"}
        columns = {row.name for row in self.sql.exec("PRAGMA table_info(users)")}
        for name,definition in additions.items():
            if name not in columns: self.sql.exec(f"ALTER TABLE users ADD COLUMN {name} {definition}")

    async def rate_limit(self, bucket, limit, window_seconds):
        now = int(time.time())
        cutoff = now - int(window_seconds)
        self.sql.exec("DELETE FROM auth_attempts WHERE attempted_at<?", cutoff)
        count = list(self.sql.exec("SELECT count(*) count FROM auth_attempts WHERE bucket=? AND attempted_at>=?", bucket, cutoff))[0].count
        if count >= int(limit):
            return False
        self.sql.exec("INSERT INTO auth_attempts VALUES(?,?)", bucket, now)
        return True

    async def register(self, username, email, password):
        uname = username.strip()
        normalized_username = uname.casefold()
        normalized_email = email.strip().casefold()
        if len(uname) < 3 or len(password) < 8 or "@" not in normalized_email:
            return {"error": "Invalid registration details"}
        if list(self.sql.exec("SELECT id FROM users WHERE username_normalized=? OR email_normalized=?", normalized_username, normalized_email)):
            return {"error": "Username or email is already in use"}
        user_id = f"usr_{secrets.token_hex(10)}"
        now = int(time.time())
        self.sql.exec("INSERT INTO users(id,username,username_normalized,email_normalized,password_hash,created_at,account_status,last_activity_at) VALUES(?,?,?,?,?,?,?,?)", user_id, uname, normalized_username, normalized_email, hash_password(password), now, "ACTIVE", now)
        self.sql.exec("INSERT INTO product_events(user_id,event_type,created_at) VALUES(?,?,?)", user_id, "registration", now)
        return {"id": user_id, "username": uname}

    async def authenticate(self, identifier, password):
        value = identifier.strip().casefold()
        rows = list(self.sql.exec("SELECT id,username,password_hash,account_status FROM users WHERE username_normalized=? OR email_normalized=? LIMIT 1", value, value))
        if not rows or rows[0].account_status != "ACTIVE" or not verify_password(password, rows[0].password_hash):
            return {"error": "Invalid username/email or password"}
        now = int(time.time())
        self.sql.exec("UPDATE users SET last_login_at=?,last_activity_at=? WHERE id=?", now, now, rows[0].id)
        self.sql.exec("INSERT INTO product_events(user_id,event_type,created_at) VALUES(?,?,?)", rows[0].id, "login", now)
        return {"id": rows[0].id, "username": rows[0].username}

    async def create_session(self,user_id,lifetime):
        session_id=secrets.token_urlsafe(24); now=int(time.time())
        self.sql.exec("DELETE FROM refresh_sessions WHERE expires_at<? OR revoked_at IS NOT NULL",now)
        self.sql.exec("INSERT INTO refresh_sessions(id,user_id,token_hash,expires_at,revoked_at) VALUES(?,?,?,?,NULL)",session_id,user_id,hashlib.sha256(session_id.encode()).hexdigest(),now+int(lifetime))
        return session_id

    async def session_active(self,user_id,session_id):
        if not session_id: return False
        digest=hashlib.sha256(session_id.encode()).hexdigest()
        return bool(list(self.sql.exec("SELECT id FROM refresh_sessions WHERE id=? AND user_id=? AND token_hash=? AND revoked_at IS NULL AND expires_at>?",session_id,user_id,digest,int(time.time()))))

    async def renew_session(self,user_id,session_id,lifetime):
        self.sql.exec("UPDATE refresh_sessions SET expires_at=? WHERE id=? AND user_id=? AND revoked_at IS NULL AND expires_at>?",int(time.time())+int(lifetime),session_id,user_id,int(time.time())); return True

    async def revoke_session(self,user_id,session_id):
        self.sql.exec("UPDATE refresh_sessions SET revoked_at=? WHERE id=? AND user_id=?",int(time.time()),session_id,user_id); return True

    async def revoke_all_sessions(self,user_id):
        self.sql.exec("UPDATE refresh_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",int(time.time()),user_id); return True

    async def username_for(self, user_id):
        rows = list(self.sql.exec("SELECT username FROM users WHERE id=? AND account_status='ACTIVE'", user_id))
        return rows[0].username if rows else None

    async def profile(self,user_id):
        rows=list(self.sql.exec("SELECT id,username,email_normalized email,display_name,timezone,date_format,language,avatar FROM users WHERE id=? AND account_status='ACTIVE'",user_id))
        if not rows: return {"error":"Account not found"}
        row=rows[0]; return {key:getattr(row,key) for key in ("id","username","email","display_name","timezone","date_format","language","avatar")}

    async def update_profile(self,user_id,display_name,timezone,date_format,language,avatar):
        if language!="en" or date_format not in ("DD/MM/YYYY","MM/DD/YYYY","YYYY-MM-DD") or avatar not in ("forest","clay","gold","ocean","plum"): return {"error":"Invalid profile settings"}
        name=str(display_name or "").strip()[:60] or None; zone=str(timezone or "UTC").strip()[:64]
        self.sql.exec("UPDATE users SET display_name=?,timezone=?,date_format=?,language=?,avatar=?,last_activity_at=? WHERE id=? AND account_status='ACTIVE'",name,zone,date_format,language,avatar,int(time.time()),user_id)
        return await self.profile(user_id)

    async def change_password(self,user_id,current_password,new_password):
        rows=list(self.sql.exec("SELECT password_hash FROM users WHERE id=? AND account_status='ACTIVE'",user_id))
        if not rows or not verify_password(current_password,rows[0].password_hash): return {"error":"Current password is incorrect"}
        if len(new_password)<10: return {"error":"New password must be at least 10 characters"}
        self.sql.exec("UPDATE users SET password_hash=?,last_activity_at=? WHERE id=?",hash_password(new_password),int(time.time()),user_id)
        self.sql.exec("DELETE FROM refresh_sessions WHERE user_id=?",user_id); return {"ok":True}

    async def record_event(self, user_id, event_type):
        now = int(time.time())
        self.sql.exec("UPDATE users SET last_activity_at=? WHERE id=?", now, user_id)
        self.sql.exec("INSERT INTO product_events(user_id,event_type,created_at) VALUES(?,?,?)", user_id, event_type, now)
        return True

    async def delete_account(self, user_id, password):
        rows = list(self.sql.exec("SELECT password_hash FROM users WHERE id=? AND account_status='ACTIVE'", user_id))
        if not rows or not verify_password(password, rows[0].password_hash):
            return {"error": "Password is incorrect"}
        now = int(time.time())
        self.sql.exec("UPDATE users SET account_status='DELETED',username='Deleted reader',username_normalized=?,email_normalized=?,password_hash='',last_activity_at=? WHERE id=?", f"deleted-{user_id}", f"deleted-{user_id}@invalid.local", now, user_id)
        self.sql.exec("DELETE FROM refresh_sessions WHERE user_id=?", user_id)
        self.sql.exec("INSERT INTO product_events(user_id,event_type,created_at) VALUES(?,?,?)", None, "account_deleted", now)
        return {"ok": True}

    async def admin_stats(self):
        now = int(time.time())
        day = now - 86400
        month = now - 30 * 86400
        def scalar(sql, *args):
            return list(self.sql.exec(sql, *args))[0].count
        totals = {"registrations": scalar("SELECT count(*) count FROM users WHERE account_status='ACTIVE'"), "logins": scalar("SELECT count(*) count FROM product_events WHERE event_type='login'"), "active_24h": scalar("SELECT count(*) count FROM users WHERE account_status='ACTIVE' AND last_activity_at>=?", day), "active_30d": scalar("SELECT count(*) count FROM users WHERE account_status='ACTIVE' AND last_activity_at>=?", month), "books_saved": scalar("SELECT count(*) count FROM product_events WHERE event_type='book_saved'"), "dna_generated": scalar("SELECT count(*) count FROM product_events WHERE event_type='dna_generated'")}
        daily = [{"day": row.day, "registrations": row.registrations, "logins": row.logins, "books_saved": row.books_saved, "dna_generated": row.dna_generated} for row in self.sql.exec("SELECT date(created_at,'unixepoch') day,sum(event_type='registration') registrations,sum(event_type='login') logins,sum(event_type='book_saved') books_saved,sum(event_type='dna_generated') dna_generated FROM product_events WHERE created_at>=? GROUP BY day ORDER BY day DESC LIMIT 14", month)]
        return {"totals": totals, "daily": daily}
