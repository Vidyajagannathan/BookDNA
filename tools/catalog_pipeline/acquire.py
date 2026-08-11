from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

USER_AGENT="BookDNA/0.2 (https://bookdna.uk; catalog metadata import)"


def request(url: str, *, headers=None, timeout=60):
    values={"User-Agent":USER_AGENT,"Accept":"application/json",**(headers or {})}
    return urlopen(Request(url,headers=values),timeout=timeout)


def download(url: str, destination: Path, *, max_bytes: int = 140*1024**3) -> dict:
    destination.parent.mkdir(parents=True,exist_ok=True); temporary=destination.with_suffix(destination.suffix+".part")
    existing=temporary.stat().st_size if temporary.exists() else 0; headers={"Range":f"bytes={existing}-"} if existing else {}
    with request(url,headers=headers,timeout=180) as response:
        mode="ab" if existing and getattr(response,"status",200)==206 else "wb"
        if mode=="wb": existing=0
        with temporary.open(mode) as stream:
            total=existing
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>max_bytes: raise RuntimeError("download exceeds configured local cap")
                stream.write(chunk)
    os.replace(temporary,destination); return {"url":url,"path":str(destination),"bytes":destination.stat().st_size}


def _append_jsonl(path: Path, items):
    path.parent.mkdir(parents=True,exist_ok=True); count=0
    with path.open("a",encoding="utf-8") as stream:
        for item in items: stream.write(json.dumps(item,ensure_ascii=False,separators=(",",":"))+"\n"); count+=1
    return count


def crossref(output: Path, *, limit: int | None = None, mailto: str | None = None, cursor="*") -> dict:
    types=("book","monograph","edited-book","reference-book","book-set","book-series"); written=0; cursors={}
    per_type=None if limit is None else max(1,limit//len(types))
    for work_type in types:
        type_written=0; type_cursor="*"
        while per_type is None or type_written<per_type:
            remaining=(per_type-type_written) if per_type is not None else 1000; rows=min(1000,remaining)
            params={"filter":f"type:{work_type}","rows":rows,"cursor":type_cursor}
            if mailto: params["mailto"]=mailto
            data=json.load(request("https://api.crossref.org/works?"+urlencode(params))); message=data.get("message",{}); items=message.get("items",[])
            if not items: break
            count=_append_jsonl(output,items); written+=count; type_written+=count; next_cursor=message.get("next-cursor")
            if not next_cursor or next_cursor==type_cursor: break
            type_cursor=next_cursor; time.sleep(.1)
        cursors[work_type]=type_cursor
        if limit and written>=limit: break
    return {"source":"crossref","records":written,"cursors":cursors,"path":str(output)}


def datacite(output: Path, *, limit: int | None = None, next_url="https://api.datacite.org/dois?query=types.resourceTypeGeneral:Book&page[size]=1000") -> dict:
    written=0
    while next_url and (not limit or written<limit):
        data=json.load(request(next_url)); items=data.get("data",[])
        if limit: items=items[:max(0,limit-written)]
        written+=_append_jsonl(output,items); next_url=(data.get("links") or {}).get("next"); time.sleep(.1)
    return {"source":"datacite","records":written,"cursor":next_url,"path":str(output)}


def doab(output: Path, *, limit: int | None = None, token: str | None = None) -> dict:
    written=0; namespace={"oai":"http://www.openarchives.org/OAI/2.0/","dc":"http://purl.org/dc/elements/1.1/"}
    while not limit or written<limit:
        url="https://directory.doabooks.org/oai/request?verb=ListRecords&metadataPrefix=oai_dc" if not token else "https://directory.doabooks.org/oai/request?verb=ListRecords&resumptionToken="+quote(token)
        root=ET.fromstring(request(url,headers={"Accept":"application/xml"}).read()); items=[]
        for record in root.findall(".//oai:record",namespace):
            header=record.find("oai:header",namespace)
            if header is not None and header.attrib.get("status")=="deleted": continue
            values={}
            for child in record.findall(".//oai:metadata/*/*",namespace): values.setdefault(child.tag.split("}")[-1],[]).append(child.text or "")
            identifier=record.findtext("oai:header/oai:identifier",default="",namespaces=namespace); items.append({"source_id":identifier,"metadata":values})
        if limit: items=items[:max(0,limit-written)]
        written+=_append_jsonl(output,items); node=root.find(".//oai:resumptionToken",namespace); token=(node.text or "").strip() if node is not None else ""
        if not token or not items: break
        time.sleep(.2)
    return {"source":"doab","records":written,"cursor":token or None,"path":str(output)}
