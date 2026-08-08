from workers import WorkerEntrypoint
import asgi
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel, Field
from js import fetch
import hashlib
import secrets
from urllib.parse import quote

from durable.identity import IdentityDO
from durable.user import UserDO
from durable.catalog import CatalogShardDO
from dna.mappings import map_subjects
from security.tokens import create_token, verify_token

app=FastAPI(title="BookDNA API",version="0.1.0",docs_url=None,redoc_url=None)

class Default(WorkerEntrypoint):
    async def fetch(self,request): return await asgi.fetch(app,request,self.env)

class RegisterBody(BaseModel):
    username:str=Field(min_length=3,max_length=30,pattern=r"^[A-Za-z0-9_]+$"); email:str=Field(max_length=254); password:str=Field(min_length=8,max_length=128)
class LoginBody(BaseModel): identifier:str=Field(min_length=1,max_length=254); password:str=Field(min_length=1,max_length=128)
class LibraryBody(BaseModel): book:dict; status:str; rating:float|None=Field(default=None,ge=.5,le=5); favourite:bool=False

def env(req): return req.scope["env"]
def secret(req):
    value=getattr(env(req),"JWT_SECRET",None)
    if not value and getattr(env(req),"APP_ENV","development")=="production":
        raise HTTPException(503,"Service authentication is not configured")
    return str(value or "local-development-only-change-me")
def identity(req): return env(req).IDENTITY.get_by_name("primary")
def current_user(req):
    token=req.cookies.get("bookdna_access"); data=verify_token(token,secret(req)) if token else None
    if not data: raise HTTPException(401,"Sign in required")
    return data
def origin_guard(req):
    origin=req.headers.get("origin"); host=req.headers.get("host")
    if origin and host and host not in origin: raise HTTPException(403,"Invalid request origin")
def set_auth(response,user,req):
    sid=secrets.token_hex(12); token=create_token(user["id"],sid,secret(req)); secure=getattr(env(req),"APP_ENV","development")=="production"
    response.set_cookie("bookdna_access",token,max_age=900,httponly=True,secure=secure,samesite="lax",path="/")

@app.get("/api/health")
async def health(): return {"status":"ok","service":"bookdna"}

@app.post("/api/auth/register")
async def register(body:RegisterBody,req:Request,response:Response):
    origin_guard(req); user=await identity(req).register(body.username,body.email,body.password)
    if user.get("error"): raise HTTPException(409,user["error"])
    await env(req).USERS.get_by_name(user["id"]).initialize(user["id"],user["username"]); set_auth(response,user,req); return user

@app.post("/api/auth/login")
async def login(body:LoginBody,req:Request,response:Response):
    origin_guard(req); user=await identity(req).authenticate(body.identifier,body.password)
    if user.get("error"): raise HTTPException(401,user["error"])
    set_auth(response,user,req); return user

@app.post("/api/auth/logout")
async def logout(req:Request,response:Response): origin_guard(req); response.delete_cookie("bookdna_access",path="/"); return {"ok":True}

@app.get("/api/auth/me")
async def me(req:Request):
    data=current_user(req); username=await identity(req).username_for(data["sub"]); return {"id":data["sub"],"username":username}

@app.get("/api/books/search")
async def search_books(q:str,req:Request):
    if len(q.strip())<2: raise HTTPException(422,"Search must be at least 2 characters")
    headers={"User-Agent":str(getattr(env(req),"OPEN_LIBRARY_USER_AGENT","BookDNA/0.1"))}; result=await fetch(f"https://openlibrary.org/search.json?q={quote(q)}&limit=12&fields=key,title,author_name,first_publish_year,cover_i,subject",{"headers":headers}); data=(await result.json()).to_py()
    books=[]
    for item in data.get("docs",[]):
        key=str(item.get("key","")).split("/")[-1]
        if not key: continue
        books.append({"id":key,"title":item.get("title","Untitled"),"author":(item.get("author_name") or ["Unknown author"])[0],"year":item.get("first_publish_year"),"cover_url":f"https://covers.openlibrary.org/b/id/{item['cover_i']}-L.jpg" if item.get("cover_i") else None,"subjects":(item.get("subject") or [])[:20]})
    return {"books":books}

@app.get("/api/library")
async def library(req:Request): data=current_user(req); return {"books":await env(req).USERS.get_by_name(data["sub"]).library()}

@app.put("/api/library/{book_id}")
async def update_library(book_id:str,body:LibraryBody,req:Request):
    origin_guard(req); data=current_user(req)
    if body.book.get("id")!=book_id: raise HTTPException(422,"Book identifier mismatch")
    traits=map_subjects(body.book.get("subjects",[])); shard=hashlib.sha256(book_id.encode()).hexdigest()[:2]; await env(req).CATALOG.get_by_name(f"catalog:{shard}").put_book(body.book,traits)
    result=await env(req).USERS.get_by_name(data["sub"]).upsert_book(body.book,body.status,body.rating,body.favourite,traits)
    if result.get("error"): raise HTTPException(422,result["error"])
    return result

@app.get("/api/dna/me")
async def dna(req:Request): data=current_user(req); return await env(req).USERS.get_by_name(data["sub"]).dna()
