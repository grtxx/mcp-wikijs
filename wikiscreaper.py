import sys
import time
import lancedb  # type: ignore
import requests # type: ignore
from lancedb.embeddings import get_registry # type: ignore
from lancedb.pydantic import LanceModel, Vector # type: ignore
import requests # type: ignore
from langchain_text_splitters import MarkdownTextSplitter # type: ignore
from configmanager import configmanager as configManager
from typing import Optional
import subprocess
from wikijsclient import WikiJSClient


cfg = configManager( "mcp-config.json" )

db = lancedb.connect( cfg.get( "lancedb_datapath" ) )
registry = get_registry().get("sentence-transformers")
model = registry.create(name=cfg.get("embedding_model_name"), device=cfg.get("embedding_model_device"))

class WikiPage(LanceModel):
    text: str = model.SourceField() # Ezt indexeli a vektoros kereső
    vector: Optional[Vector(model.ndims())] = model.VectorField(default=None) # type: ignore # Automatikus embedding
    page_id: int
    title: str
    url: str
    description: str
    updatedAt: str

table_name = cfg.get("collection_name")

if table_name in db.list_tables().tables:
    table = db.open_table(table_name)
else:
    # Ha új, létrehozzuk üresen a sémával
    table = db.create_table(table_name, schema=WikiPage)


def main():
    wiki = WikiJSClient( cfg.get( "wiki_url" ), cfg.get( "wiki_token" ) ) # type: ignore

    lastrun = cfg.get('lastrun')
    if ( lastrun is None ) or ( lastrun == "" ):
        lastrun = "1970-01-01T00:00:00Z"

    cfg.set('lastrun', time.strftime( '%Y-%m-%dT%H:%M:%SZ', time.gmtime() ))

    print("Oldalak listázása...")
    pages = wiki.get_all_pages()
    
    text_splitter = MarkdownTextSplitter(
        chunk_size=cfg.get("chunk_size"), 
        chunk_overlap=cfg.get("chunk_overlap"), 
        length_function=len,
    )

    cnt = 0
    skip = 0

    for p in pages:
        page_id = p['id']
        title = p['title']
        path = p['path']

        if p["updatedAt"] < lastrun:
            skip += 1
            print(f"Skip: {title} ({path})...")
            continue
        cnt += 1
        print(f"Loading: {title} ({path})...")
        try:
            table.delete( f"page_id = {page_id}" )
        except:
            pass

       
        page = wiki.convertToMarkdown( wiki.getPage(int(page_id) ) )
        url = f"{cfg.get('wiki_url').rstrip('/graphql')}/{page['locale']}/{path}" # type: ignore

        chunks = text_splitter.split_text( page['content'] ) # type: ignore
        chunkList = []
        if chunks:
            for c in chunks:
                c = f"### {title}\n{page['description']}\n----- \n\n{c}" # type: ignore
                chunkList.append( WikiPage(
                    text = f"passage: {c}",
                    page_id = int(page_id),
                    title = page['title'], # type: ignore
                    url = url,
                    description = page['description'], # type: ignore
                    updatedAt = p['updatedAt']
                ) )
            table.add( chunkList )

    if cnt > 0:
        print( "Indexelés..." )
        table.create_fts_index( "text", replace=True )

        print( "Karbantartás..." )
        for i in range(3):
            try:
                table.optimize()
                break
            except:
                print( "Concurrency during optimization, retrying..." )
                time.sleep(2)
                pass
        #table.cleanup_old_versions()

    print(f"\nKész! {cnt} oldal beindexelve, {skip} oldal kihagyva.")
    cfg.saveConfig()

if __name__ == "__main__":
    main()