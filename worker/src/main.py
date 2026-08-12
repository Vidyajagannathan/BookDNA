from workers import WorkerEntrypoint, Response
from durable.identity import IdentityDO
from durable.user import UserDO
from durable.catalog import CatalogShardDO
from dna.mappings import map_subjects
from security.tokens import create_token, verify_token
from js import fetch, Object, Request
from pyodide.ffi import to_js as _to_js
from urllib.parse import urlparse, parse_qs, quote, unquote
import hashlib
import secrets
import json
import traceback
import re
import asyncio
import base64

def native(value):
    """Convert values crossing the JS/Durable Object RPC boundary."""
    return value.to_py() if hasattr(value,"to_py") else value

def js_object(value):
    """Convert Python mappings into plain JavaScript objects for Web APIs."""
    return _to_js(value,dict_converter=Object.fromEntries)

def reply(data, status=200, headers=None):
    base={"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}
    if headers: base.update(headers)
    return Response(json.dumps(data,separators=(",",":")),status=status,headers=base)

def cookies(request):
    result={}
    for part in (request.headers.get("Cookie") or "").split(";"):
        if "=" in part:
            key,value=part.strip().split("=",1); result[key]=value
    return result

class Default(WorkerEntrypoint):
    def signing_secret(self):
        value=getattr(self.env,"JWT_SECRET",None)
        if not value and getattr(self.env,"APP_ENV","development")=="production": raise RuntimeError("Authentication is not configured")
        return str(value or "local-development-only-change-me")

    def user(self,request):
        token=cookies(request).get("bookdna_access"); return verify_token(token,self.signing_secret()) if token else None

    def origin_ok(self,request):
        origin=request.headers.get("Origin"); host=request.headers.get("Host")
        if not origin or not host: return True
        if getattr(self.env,"APP_ENV","development")!="production": return True
        parsed=urlparse(origin)
        return parsed.scheme=="https" and parsed.netloc==host

    def auth_cookie(self,user):
        token=create_token(user["id"],secrets.token_hex(12),self.signing_secret())
        secure="; Secure" if getattr(self.env,"APP_ENV","development")=="production" else ""
        return f"bookdna_access={token}; Path=/; Max-Age=900; HttpOnly; SameSite=Lax{secure}"

    def client_key(self,request):
        return str(request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For") or "local").split(",")[0].strip()

    def is_admin(self,request):
        user=self.user(request); configured=str(getattr(self.env,"ADMIN_USER_IDS","")).split(",")
        return bool(user and user.get("sub") in {value.strip() for value in configured if value.strip()})

    async def fetch(self,request):
        try:
            url=urlparse(request.url); path=url.path; method=request.method.upper()
            if not path.startswith("/api/"):
                app_routes={"/","/discover","/search","/dna","/login","/register","/account","/admin","/privacy","/terms"}
                if "." in path.rsplit("/",1)[-1]: return await self.env.ASSETS.fetch(request)
                shell_request=Request.new(f"{url.scheme}://{url.netloc}/index.html")
                shell=await self.env.ASSETS.fetch(shell_request)
                if path in app_routes or path.startswith("/library"): return shell
                return Response(await shell.text(),status=404,headers=shell.headers)
            if method in ("POST","PUT","PATCH","DELETE") and not self.origin_ok(request): return reply({"detail":"Invalid request origin"},403)
            if path=="/api/health" and method=="GET": return reply({"status":"ok","service":"bookdna","build":"global-catalog-20260811"})
            if path=="/api/auth/register" and method=="POST": return await self.register(request)
            if path=="/api/auth/login" and method=="POST": return await self.login(request)
            if path=="/api/auth/logout" and method=="POST": return reply({"ok":True},headers={"Set-Cookie":"bookdna_access=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"})
            if path=="/api/auth/me" and method=="GET": return await self.me(request)
            if path=="/api/auth/profile" and method=="GET": return await self.profile(request)
            if path=="/api/auth/profile" and method=="PUT": return await self.update_profile(request)
            if path=="/api/auth/password" and method=="PUT": return await self.change_password(request)
            if path=="/api/auth/account" and method=="DELETE": return await self.delete_account(request)
            if path=="/api/admin/stats" and method=="GET": return await self.admin_stats(request)
            if path=="/api/books/search" and method=="GET": return await self.search(parse_qs(url.query))
            if path=="/api/books/catalog/status" and method=="GET": return await self.catalog_status()
            if path.startswith("/api/books/isbn/") and method=="GET": return await self.by_isbn(unquote(path.removeprefix("/api/books/isbn/")))
            if path.startswith("/api/books/") and path.endswith("/editions") and method=="GET": return await self.book_editions(unquote(path.removeprefix("/api/books/").removesuffix("/editions")))
            if path=="/api/books/collections" and method=="GET": return reply({"collections":[
                {"id":"fantasy","name":"Fantasy","query":"subject:fantasy"},{"id":"science-fiction","name":"Science fiction","query":"subject:science fiction"},
                {"id":"romance","name":"Romance","query":"subject:romance"},{"id":"mystery","name":"Mystery & thrillers","query":"subject:mystery"},
                {"id":"history","name":"History","query":"subject:history"},{"id":"biography","name":"Biography & memoir","query":"subject:biography"},
                {"id":"philosophy","name":"Philosophy","query":"subject:philosophy"},{"id":"classics","name":"Classics","query":"subject:classics"},
                {"id":"horror","name":"Horror","query":"subject:horror"},{"id":"crime","name":"Crime","query":"subject:crime"},
                {"id":"adventure","name":"Adventure","query":"subject:adventure"},{"id":"historical-fiction","name":"Historical fiction","query":"subject:historical fiction"},
                {"id":"young-adult","name":"Young adult","query":"subject:young adult"},{"id":"children","name":"Children's","query":"subject:children"},
                {"id":"poetry","name":"Poetry","query":"subject:poetry"},{"id":"science","name":"Science","query":"subject:science"},
                {"id":"psychology","name":"Psychology","query":"subject:psychology"},{"id":"travel","name":"Travel","query":"subject:travel"},
                {"id":"art","name":"Art & design","query":"subject:art"},{"id":"humour","name":"Humour","query":"subject:humor"}
            ]})
            if path.startswith("/api/books/") and method=="GET": return await self.book_detail(unquote(path.removeprefix("/api/books/")))
            if path=="/api/library" and method=="GET": return await self.library(request)
            if path.startswith("/api/library/") and method=="DELETE": return await self.remove_library_book(request,unquote(path.removeprefix("/api/library/")))
            if path.startswith("/api/library/") and method=="PUT": return await self.update_library(request,unquote(path.removeprefix("/api/library/")))
            if path.startswith("/api/recommendations/") and method=="GET": return await self.recommendations(request,unquote(path.removeprefix("/api/recommendations/")))
            if path=="/api/dna/me" and method=="GET": return await self.dna(request)
            return reply({"detail":"Not found"},404)
        except Exception as exc:
            print(f"BookDNA request error: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            return reply({"detail":"Internal service error"},500)

    async def body(self,request):
        return native(await request.json())

    async def register(self,request):
        body=await self.body(request); username=str(body.get("username","")).strip(); email=str(body.get("email","")).strip(); password=str(body.get("password",""))
        if len(username)<3 or len(username)>30 or not username.replace("_","").isalnum() or "@" not in email or len(password)<8: return reply({"detail":"Invalid registration details"},422)
        identity=self.env.IDENTITY.getByName("primary")
        if not await identity.rate_limit(f"register:{self.client_key(request)}",5,3600): return reply({"detail":"Too many registration attempts. Please try again later."},429)
        user=native(await identity.register(username,email,password))
        if user.get("error"): return reply({"detail":user["error"]},409)
        await self.env.USERS.getByName(user["id"]).initialize(user["id"],user["username"])
        return reply(user,headers={"Set-Cookie":self.auth_cookie(user)})

    async def login(self,request):
        body=await self.body(request); identity=self.env.IDENTITY.getByName("primary"); identifier=str(body.get("identifier","")).strip().casefold(); bucket=hashlib.sha256(identifier.encode()).hexdigest()[:20]
        if not await identity.rate_limit(f"login:{self.client_key(request)}:{bucket}",10,900): return reply({"detail":"Too many login attempts. Please wait and try again."},429)
        user=native(await identity.authenticate(identifier,str(body.get("password",""))))
        if user.get("error"): return reply({"detail":user["error"]},401)
        return reply(user,headers={"Set-Cookie":self.auth_cookie(user)})

    async def me(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        username=await self.env.IDENTITY.getByName("primary").username_for(user["sub"]); return reply({"id":user["sub"],"username":username})

    async def profile(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        return reply(native(await self.env.IDENTITY.getByName("primary").profile(user["sub"])))

    async def update_profile(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        body=await self.body(request); result=native(await self.env.IDENTITY.getByName("primary").update_profile(user["sub"],body.get("display_name"),body.get("timezone"),body.get("date_format"),body.get("language"),body.get("avatar")))
        return reply({"detail":result["error"]},422) if result.get("error") else reply(result)

    async def change_password(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        body=await self.body(request); result=native(await self.env.IDENTITY.getByName("primary").change_password(user["sub"],str(body.get("current_password","")),str(body.get("new_password",""))))
        if result.get("error"): return reply({"detail":result["error"]},422)
        return reply(result,headers={"Set-Cookie":self.auth_cookie({"id":user["sub"]})})

    async def delete_account(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        body=await self.body(request); result=native(await self.env.IDENTITY.getByName("primary").delete_account(user["sub"],str(body.get("password",""))))
        if result.get("error"): return reply({"detail":result["error"]},403)
        await self.env.USERS.getByName(user["sub"]).delete_account_data()
        return reply({"ok":True},headers={"Set-Cookie":"bookdna_access=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"})

    async def admin_stats(self,request):
        if not self.is_admin(request): return reply({"detail":"Not found"},404)
        return reply(native(await self.env.IDENTITY.getByName("primary").admin_stats()))

    def book_from_openlibrary(self,item):
        key=str(item.get("key","")).split("/")[-1]
        return {"id":key,"title":item.get("title","Untitled"),"author":(item.get("author_name") or ["Unknown author"])[0],"year":item.get("first_publish_year"),"cover_url":f"https://covers.openlibrary.org/b/id/{item['cover_i']}-L.jpg" if item.get("cover_i") else None,"subjects":(item.get("subject") or [])[:20],"edition_count":item.get("edition_count",0),"isbn":(item.get("isbn") or [])[:10],"source":"openlibrary"}

    async def cache_books(self,books):
        database=getattr(self.env,"CATALOG_DB",None)
        if not database: return
        for book in books:
            try:
                cover_id=None
                if book.get("cover_url"):
                    match=re.search(r"/b/id/(\d+)-",book["cover_url"]); cover_id=int(match.group(1)) if match else None
                await database.prepare("INSERT INTO catalog_works(id,title,author,first_publish_year,cover_id,subjects_json,source,updated_at) VALUES(?,?,?,?,?,?,?,unixepoch()) ON CONFLICT(id) DO UPDATE SET title=excluded.title,author=excluded.author,first_publish_year=excluded.first_publish_year,cover_id=excluded.cover_id,subjects_json=excluded.subjects_json,updated_at=excluded.updated_at").bind(book["id"],book["title"],book["author"],book.get("year"),cover_id,json.dumps(book.get("subjects",[])),book.get("source","openlibrary")).run()
                await database.prepare("DELETE FROM catalog_works_fts WHERE id=?").bind(book["id"]).run()
                await database.prepare("INSERT INTO catalog_works_fts(id,title,author,subjects) VALUES(?,?,?,?)").bind(book["id"],book["title"],book["author"]," ".join(book.get("subjects",[]))).run()
            except Exception as exc:
                print(f"Catalog cache warning: {type(exc).__name__}: {exc}")

    def search_shards(self):
        return [binding for index in range(8) if (binding:=getattr(self.env,f"CATALOG_SEARCH_{index}",None)) is not None]

    def search_terms(self,query):
        value=query.split(":",1)[-1] if query.startswith("subject:") else query
        words=re.findall(r"[\w]+",value,flags=re.UNICODE)[:8]
        return " AND ".join(f'"{word.replace(chr(34),"")}"*' for word in words)

    async def local_shard_search(self,database,query,limit,offset,language=None,year_from=None,year_to=None,format_name=None):
        terms=self.search_terms(query)
        if not terms: return []
        clauses=["search_works_fts MATCH ?"]; values=[terms]
        if language: clauses.append("w.language=?"); values.append(language)
        if year_from: clauses.append("CAST(substr(w.published,1,4) AS INTEGER)>=?"); values.append(year_from)
        if year_to: clauses.append("CAST(substr(w.published,1,4) AS INTEGER)<=?"); values.append(year_to)
        if format_name: clauses.append("lower(w.format)=lower(?)"); values.append(format_name)
        sql=f"SELECT w.*,bm25(search_works_fts) rank FROM search_works_fts JOIN search_works w ON w.id=search_works_fts.id WHERE {' AND '.join(clauses)} ORDER BY rank,CASE w.quality WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END,w.edition_count DESC LIMIT ? OFFSET ?"
        values.extend([limit,offset]); result=native(await database.prepare(sql).bind(*values).all())
        return result.get("results",[]) if isinstance(result,dict) else []

    def local_book(self,row):
        cover=row.get("cover_url"); year=None
        if row.get("published"):
            match=re.search(r"(?:1[0-9]{3}|20[0-9]{2})",str(row["published"])); year=int(match.group()) if match else None
        return {"id":row["id"],"title":row.get("title") or "Untitled","author":row.get("author") or "Unknown author","year":year,"cover_url":cover,"subjects":[],"edition_count":int(row.get("edition_count") or 0),"source":"catalog","quality":row.get("quality"),"language":row.get("language"),"format":row.get("format"),"sources":json.loads(row.get("sources_json") or "[]")}

    async def local_search(self,query,limit,offset,language=None,year_from=None,year_to=None,format_name=None):
        shards=self.search_shards()
        if not shards: return []
        rows=[]
        results=await asyncio.gather(*(self.local_shard_search(database,query,limit,offset,language,year_from,year_to,format_name) for database in shards))
        for result in results: rows.extend(result)
        rows.sort(key=lambda row:(float(row.get("rank",0)),{"A":0,"B":1,"C":2}.get(row.get("quality"),3),-int(row.get("edition_count") or 0)))
        return [self.local_book(row) for row in rows[:limit]]

    async def search(self,params):
        query=str(params.get("q",[""])[0]).strip(); page=max(1,min(100,int(params.get("page",["1"])[0] or 1))); limit=max(4,min(40,int(params.get("limit",["24"])[0] or 24)))
        cursor=str(params.get("cursor",[""])[0]); offset=(page-1)*limit
        if cursor:
            try: offset=max(0,int(base64.urlsafe_b64decode(cursor+"===").decode()))
            except Exception: return reply({"detail":"Invalid search cursor"},422)
        if len(query)<2: return reply({"detail":"Search must be at least 2 characters"},422)
        language=str(params.get("language",[""])[0]).strip() or None; format_name=str(params.get("format",[""])[0]).strip() or None
        try: year_from=int(params.get("year_from",["0"])[0] or 0) or None; year_to=int(params.get("year_to",["0"])[0] or 0) or None
        except ValueError: return reply({"detail":"Invalid year filter"},422)
        mode=await self.catalog_mode(); local=[]
        try: local=await self.local_search(query,limit,offset,language,year_from,year_to,format_name)
        except Exception as exc: print(f"Local catalog search warning: {type(exc).__name__}: {exc}")
        visible_local=local if mode in ("hybrid","local-first") else []
        if len(visible_local)>=limit:
            next_cursor=base64.urlsafe_b64encode(str(offset+limit).encode()).decode().rstrip("=")
            return reply({"books":visible_local,"page":page,"limit":limit,"total":None,"has_more":True,"cursor":next_cursor,"source":"catalog"})
        options=js_object({"headers":{"User-Agent":str(getattr(self.env,"OPEN_LIBRARY_USER_AGENT","BookDNA/0.1"))}})
        try: result=await asyncio.wait_for(fetch(f"https://openlibrary.org/search.json?q={quote(query)}&page={page}&limit={limit}&fields=key,title,author_name,first_publish_year,cover_i,subject,edition_count,isbn",options),8)
        except asyncio.TimeoutError: return reply({"detail":"The book catalog took too long to respond. Please try again."},504)
        if not result.ok: return reply({"detail":"The global book catalog is temporarily unavailable"},502)
        data=native(await result.json()); remote=[self.book_from_openlibrary(item) for item in data.get("docs",[]) if item.get("key")]
        seen={book["id"] for book in visible_local}; books=visible_local+[book for book in remote if book["id"] not in seen]; books=books[:limit]
        # Search results do not wait for optional cache writes; local catalog imports own persistence.
        total=int(data.get("numFound",0)); next_cursor=base64.urlsafe_b64encode(str(offset+limit).encode()).decode().rstrip("=")
        return reply({"books":books,"page":page,"limit":limit,"total":total,"has_more":page*limit<total,"cursor":next_cursor,"source":"hybrid" if visible_local else "openlibrary"})

    async def catalog_mode(self):
        database=getattr(self.env,"CATALOG_DB",None)
        if not database: return "fallback"
        try:
            row=native(await database.prepare("SELECT value FROM catalog_settings WHERE key='mode'").first())
            return str(row.get("value","shadow")) if isinstance(row,dict) else "shadow"
        except Exception: return "shadow"

    async def catalog_status(self):
        database=getattr(self.env,"CATALOG_DB",None)
        if not database: return reply({"mode":"fallback","sources":[],"indexed":0,"archive_bytes":0})
        settings=native(await database.prepare("SELECT key,value FROM catalog_settings").all()); stats=native(await database.prepare("SELECT * FROM catalog_source_stats ORDER BY source").all())
        indexed=0
        for shard in self.search_shards():
            try:
                result=native(await shard.prepare("SELECT count(*) count FROM search_works").first()); indexed+=int(result.get("count",0)) if isinstance(result,dict) else 0
            except Exception: pass
        values={row["key"]:row["value"] for row in settings.get("results",[])}
        return reply({"mode":values.get("mode","shadow"),"sources":stats.get("results",[]),"indexed":indexed,"archive_bytes":int(values.get("archive_bytes","0")),"quality":json.loads(values.get("quality","{}")),"last_refresh":values.get("last_refresh")})

    async def book_detail(self,book_id):
        for shard in self.search_shards():
            row=native(await shard.prepare("SELECT * FROM search_works WHERE id=?").bind(book_id).first())
            if row: return reply({"book":self.local_book(row),"editions":[]})
        cached=await self.env.CATALOG.getByName(f"catalog:{hashlib.sha256(book_id.encode()).hexdigest()[:2]}").get_book(book_id)
        if cached: return reply(native(cached))
        return reply({"detail":"Book not found"},404)

    async def book_editions(self,book_id):
        identifiers=getattr(self.env,"CATALOG_IDENTIFIERS",None)
        if not identifiers: return reply({"work_id":book_id,"editions":[]})
        result=native(await identifiers.prepare("SELECT edition_id,payload_json FROM catalog_identifiers WHERE work_id=? GROUP BY edition_id ORDER BY edition_id LIMIT 100").bind(book_id).all())
        rows=result.get("results",[]) if isinstance(result,dict) else []
        editions=[]
        for row in rows:
            item=json.loads(row["payload_json"]); item["id"]=row["edition_id"]; editions.append(item)
        return reply({"work_id":book_id,"editions":editions})

    async def by_isbn(self,isbn):
        normalized=re.sub(r"[^0-9X]","",isbn.upper())
        if len(normalized) not in (10,13): return reply({"detail":"Invalid ISBN"},422)
        if len(normalized)==10:
            stem="978"+normalized[:9]; normalized=stem+str((10-sum((1 if index%2==0 else 3)*int(value) for index,value in enumerate(stem))%10)%10)
        identifiers=getattr(self.env,"CATALOG_IDENTIFIERS",None)
        if identifiers:
            try:
                result=native(await identifiers.prepare("SELECT payload_json FROM catalog_identifiers WHERE scheme='isbn' AND value=? LIMIT 10").bind(normalized).all()); rows=result.get("results",[]) if isinstance(result,dict) else []
                matches=[]
                for row in rows:
                    item=json.loads(row["payload_json"]); matches.append({"id":item.get("work_id") or item.get("work_hint") or item.get("source_id"),"title":item.get("title","Untitled"),"author":next(iter(item.get("authors") or ["Unknown author"])),"year":int(match.group()) if (match:=re.search(r"(?:1[0-9]{3}|20[0-9]{2})",str(item.get("published") or ""))) else None,"cover_url":item.get("cover_url"),"subjects":item.get("subjects",[]),"source":"catalog","quality":"A","language":item.get("language"),"format":item.get("format")})
                if matches: return reply({"book":matches[0],"matches":matches,"source":"catalog"})
            except Exception as exc: print(f"Identifier lookup warning: {type(exc).__name__}: {exc}")
        options=js_object({"headers":{"User-Agent":str(getattr(self.env,"OPEN_LIBRARY_USER_AGENT","BookDNA/0.1"))}})
        result=await fetch(f"https://openlibrary.org/search.json?isbn={quote(normalized)}&limit=10&fields=key,title,author_name,first_publish_year,cover_i,subject,edition_count,isbn",options)
        data=native(await result.json()); books=[self.book_from_openlibrary(item) for item in data.get("docs",[]) if item.get("key")]
        if not books: return reply({"detail":"ISBN not found"},404)
        await self.cache_books(books); return reply({"book":books[0],"matches":books,"source":"openlibrary"})

    async def library(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        return reply({"books":native(await self.env.USERS.getByName(user["sub"]).library())})

    async def update_library(self,request,book_id):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        body=await self.body(request); book=body.get("book",{}); status=body.get("status"); rating=body.get("rating"); favourite=bool(body.get("favourite",False)); dnf_reason=body.get("dnf_reason")
        if book.get("id")!=book_id or status not in ("READ","CURRENTLY_READING","WANT_TO_READ","DNF") or (rating is not None and (float(rating)<.5 or float(rating)>5)) or (dnf_reason is not None and (not isinstance(dnf_reason,str) or len(dnf_reason)>500)): return reply({"detail":"Invalid library update"},422)
        traits=map_subjects(book.get("subjects",[])); shard=hashlib.sha256(book_id.encode()).hexdigest()[:2]; await self.env.CATALOG.getByName(f"catalog:{shard}").put_book(book,traits); result=native(await self.env.USERS.getByName(user["sub"]).upsert_book(book,status,rating,favourite,traits,dnf_reason))
        await self.env.IDENTITY.getByName("primary").record_event(user["sub"],"book_saved")
        return reply(result)

    async def remove_library_book(self,request,book_id):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        result=native(await self.env.USERS.getByName(user["sub"]).remove_book(book_id))
        if result.get("error"): return reply({"detail":result["error"]},404)
        await self.env.IDENTITY.getByName("primary").record_event(user["sub"],"book_removed"); return reply(result)

    async def recommendations(self,request,book_id):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        library=native(await self.env.USERS.getByName(user["sub"]).library()); source=next((book for book in library if book.get("id")==book_id),None)
        if not source: return reply({"detail":"Book not found in your library"},404)
        excluded={book["id"] for book in library}; subjects=[str(value) for value in source.get("subjects",[]) if len(str(value))<80][:4]; theme_query="subject:"+(subjects[0] if subjects else " ".join(map_subjects(source.get("subjects",[]))[0]["name"].split()) if map_subjects(source.get("subjects",[])) else source["title"])
        async def find(query):
            result=await self.search({"q":[query],"limit":["12"],"page":["1"]}); data=native(await result.json()); return data.get("books",[])
        themed,author=await asyncio.gather(find(theme_query),find(f'author:{source.get("author","")}'))
        def clean(items,kind):
            output=[]
            for book in items:
                if book["id"] in excluded or book["id"]==book_id or any(existing["id"]==book["id"] for existing in output): continue
                shared=[subject for subject in subjects if any(subject.casefold() in candidate.casefold() or candidate.casefold() in subject.casefold() for candidate in book.get("subjects",[]))][:3]
                book["reason"]=(f"Shares themes and subjects: {', '.join(shared)}" if shared else "Related through the catalog’s subject metadata") if kind=="similar" else f"Another work by {source.get('author')}"
                output.append(book)
                if len(output)>=6: break
            return output
        return reply({"source":source,"similar":clean(themed,"similar"),"by_author":clean(author,"author"),"basis":"Recommendations use catalog subjects, themes, authorship, and your existing library—not invented plot or character analysis."})

    async def dna(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        result=native(await self.env.USERS.getByName(user["sub"]).dna()); await self.env.IDENTITY.getByName("primary").record_event(user["sub"],"dna_generated"); return reply(result)
