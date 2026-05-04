import time
from lancedb.embeddings import get_registry # type: ignore
from lancedb.pydantic import LanceModel, Vector # type: ignore
from langchain_text_splitters import MarkdownTextSplitter # type: ignore
from configmanager import config as cfg
from typing import Optional
from wikijsclient import WikiJSClient
import kbvector


def main():
    VectorDB = kbvector.WikiVector( datapath=cfg.get( "lancedb_datapath" ), 
                                        embedding_model_name=cfg.get("embedding_model_name"), 
                                        embedding_model_device=cfg.get("embedding_model_device"), 
                                        collection_name=cfg.get("collection_name"), 
                                        chunk_size=int(cfg.get("chunk_size")), # type: ignore
                                        chunk_overlap=int(cfg.get("chunk_overlap")) ) # type: ignore
    
    wiki = WikiJSClient( cfg.get( "wiki_url" ), cfg.get( "wiki_token" ) ) # type: ignore

    lastrun = cfg.get('lastrun')
    cfg.set('lastrun', time.strftime( '%Y-%m-%dT%H:%M:%SZ', time.gmtime() ))

    print("Oldalak listázása...")
    pages = wiki.get_all_pages()
    
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
       
        page = wiki.convertToMarkdown( wiki.getPage(int(page_id) ) )
        url = f"{cfg.get('wiki_url').rstrip('/graphql')}/{page['locale']}/{path}" # type: ignore

        pg = kbvector.Page()
        pg.source = "wikijs"
        pg.page_id = page_id
        pg.title = title
        pg.url = url
        pg.text = page['content'] # type: ignore
        pg.description = page['description'] if 'description' in page else "" # type: ignore
        pg.updatedAt = p['updatedAt'] # type: ignore

        VectorDB.addPage( pg )

    if cnt > 0:
        print( "Indexelés..." )
        VectorDB.maintenance()

    print(f"\nKész! {cnt} oldal beindexelve, {skip} oldal kihagyva.")
    cfg.saveConfig()

if __name__ == "__main__":
    main()