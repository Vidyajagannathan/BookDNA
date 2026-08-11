from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .pipeline import CatalogPipeline
from . import sources
from . import acquire

PARSERS={"crossref":sources.crossref,"datacite":sources.datacite,"doab":sources.doab_oai}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Build BookDNA's free, provenance-aware book catalog")
    parser.add_argument("--workspace",type=Path,default=Path.home()/"BookDNA-catalog-work")
    commands=parser.add_subparsers(dest="command",required=True)
    ingest=commands.add_parser("ingest"); ingest.add_argument("source",choices=("openlibrary","loc","crossref","datacite","doab","gutenberg")); ingest.add_argument("path",type=Path); ingest.add_argument("--limit",type=int)
    authors=commands.add_parser("ingest-openlibrary-authors"); authors.add_argument("path",type=Path); authors.add_argument("--limit",type=int)
    commands.add_parser("report")
    archive=commands.add_parser("export-archive"); archive.add_argument("output",type=Path)
    index=commands.add_parser("export-d1"); index.add_argument("output",type=Path); index.add_argument("--incremental",action="store_true")
    identifiers=commands.add_parser("export-identifiers"); identifiers.add_argument("output",type=Path); identifiers.add_argument("--incremental",action="store_true")
    fetch=commands.add_parser("fetch"); fetch.add_argument("source",choices=("crossref","datacite","doab")); fetch.add_argument("output",type=Path); fetch.add_argument("--limit",type=int); fetch.add_argument("--mailto")
    get=commands.add_parser("download"); get.add_argument("url"); get.add_argument("output",type=Path)
    args=parser.parse_args(argv); pipeline=CatalogPipeline(args.workspace)
    try:
        if args.command=="ingest":
            if args.source=="openlibrary": records=sources.read_openlibrary(args.path,pipeline.openlibrary_author_map())
            elif args.source=="loc": records=sources.read_marc(args.path)
            elif args.source=="gutenberg": records=sources.read_csv(args.path)
            else: records=sources.read_jsonl(args.path,PARSERS[args.source])
            result=pipeline.ingest(args.source,records,limit=args.limit); print(json.dumps(result,indent=2))
        elif args.command=="ingest-openlibrary-authors": print(json.dumps(pipeline.ingest_openlibrary_authors(sources.read_openlibrary_authors(args.path),limit=args.limit),indent=2))
        elif args.command=="report": print(json.dumps(pipeline.report(),indent=2))
        elif args.command=="export-archive": print(json.dumps(pipeline.export_archive(args.output),indent=2))
        elif args.command=="export-d1": print(json.dumps(pipeline.export_d1(args.output,incremental=args.incremental),indent=2))
        elif args.command=="export-identifiers": print(json.dumps(pipeline.export_identifiers(args.output,incremental=args.incremental),indent=2))
        elif args.command=="fetch":
            function=getattr(acquire,args.source); keywords={"limit":args.limit}
            if args.source=="crossref": keywords["mailto"]=args.mailto
            print(json.dumps(function(args.output,**keywords),indent=2))
        elif args.command=="download": print(json.dumps(acquire.download(args.url,args.output),indent=2))
    finally: pipeline.close()


if __name__=="__main__": main()
