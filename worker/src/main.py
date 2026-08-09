from workers import WorkerEntrypoint, Response
from durable.identity import IdentityDO
from durable.user import UserDO
from durable.catalog import CatalogShardDO
from dna.mappings import map_subjects
from security.tokens import create_token, verify_token
from js import fetch, Object
from pyodide.ffi import to_js as _to_js
from urllib.parse import urlparse, parse_qs, quote, unquote
import hashlib
import secrets
import json
import traceback

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

    async def fetch(self,request):
        try:
            url=urlparse(request.url); path=url.path; method=request.method.upper()
            if not path.startswith("/api/"): return await self.env.ASSETS.fetch(request)
            if method in ("POST","PUT","PATCH","DELETE") and not self.origin_ok(request): return reply({"detail":"Invalid request origin"},403)
            if path=="/api/health" and method=="GET": return reply({"status":"ok","service":"bookdna","build":"auth-rpc-fix-20260809"})
            if path=="/api/auth/register" and method=="POST": return await self.register(request)
            if path=="/api/auth/login" and method=="POST": return await self.login(request)
            if path=="/api/auth/logout" and method=="POST": return reply({"ok":True},headers={"Set-Cookie":"bookdna_access=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"})
            if path=="/api/auth/me" and method=="GET": return await self.me(request)
            if path=="/api/books/search" and method=="GET": return await self.search(parse_qs(url.query).get("q",[""])[0])
            if path=="/api/library" and method=="GET": return await self.library(request)
            if path.startswith("/api/library/") and method=="PUT": return await self.update_library(request,unquote(path.removeprefix("/api/library/")))
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
        identity=self.env.IDENTITY.getByName("primary"); user=native(await identity.register(username,email,password))
        if user.get("error"): return reply({"detail":user["error"]},409)
        await self.env.USERS.getByName(user["id"]).initialize(user["id"],user["username"])
        return reply(user,headers={"Set-Cookie":self.auth_cookie(user)})

    async def login(self,request):
        body=await self.body(request); user=native(await self.env.IDENTITY.getByName("primary").authenticate(str(body.get("identifier","")),str(body.get("password",""))))
        if user.get("error"): return reply({"detail":user["error"]},401)
        return reply(user,headers={"Set-Cookie":self.auth_cookie(user)})

    async def me(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        username=await self.env.IDENTITY.getByName("primary").username_for(user["sub"]); return reply({"id":user["sub"],"username":username})

    async def search(self,query):
        if len(query.strip())<2: return reply({"detail":"Search must be at least 2 characters"},422)
        options=js_object({"headers":{"User-Agent":str(getattr(self.env,"OPEN_LIBRARY_USER_AGENT","BookDNA/0.1"))}})
        result=await fetch(f"https://openlibrary.org/search.json?q={quote(query)}&limit=12&fields=key,title,author_name,first_publish_year,cover_i,subject",options); data=native(await result.json()); books=[]
        for item in data.get("docs",[]):
            key=str(item.get("key","")).split("/")[-1]
            if key: books.append({"id":key,"title":item.get("title","Untitled"),"author":(item.get("author_name") or ["Unknown author"])[0],"year":item.get("first_publish_year"),"cover_url":f"https://covers.openlibrary.org/b/id/{item['cover_i']}-L.jpg" if item.get("cover_i") else None,"subjects":(item.get("subject") or [])[:20]})
        return reply({"books":books})

    async def library(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        return reply({"books":native(await self.env.USERS.getByName(user["sub"]).library())})

    async def update_library(self,request,book_id):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        body=await self.body(request); book=body.get("book",{}); status=body.get("status"); rating=body.get("rating"); favourite=bool(body.get("favourite",False))
        if book.get("id")!=book_id or status not in ("READ","CURRENTLY_READING","WANT_TO_READ","DNF") or (rating is not None and (float(rating)<.5 or float(rating)>5)): return reply({"detail":"Invalid library update"},422)
        traits=map_subjects(book.get("subjects",[])); shard=hashlib.sha256(book_id.encode()).hexdigest()[:2]; await self.env.CATALOG.getByName(f"catalog:{shard}").put_book(book,traits); result=native(await self.env.USERS.getByName(user["sub"]).upsert_book(book,status,rating,favourite,traits))
        return reply(result)

    async def dna(self,request):
        user=self.user(request)
        if not user: return reply({"detail":"Sign in required"},401)
        return reply(native(await self.env.USERS.getByName(user["sub"]).dna()))
