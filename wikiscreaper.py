import time
from configmanager import config as cfg
from wikijsclient import WikiJSClient
import teivector
import lancedb


def main():
    db = lancedb.connect( cfg.get( "lancedb_datapath", "" ) ) # type: ignore

    VectorDB = teivector.TEIVector( 
        db=db,
        tei_url=cfg.get( "tei_server" ),
        schemastring="source:str,page_id:str,title:str,url:str,description:str,updatedAt:str",
        model_dims=int(cfg.get("model_dims")), # type: ignore
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
        pg = {
            "source": "wikijs",
            "page_id": page_id,
            "title": title,
            "url": url,
            "description": page['description'] if 'description' in page else "", # type: ignore
            "updatedAt": p['updatedAt'] # type: ignore
        }

        VectorDB.longTextAdd( page['content'], idField="page_id", metadata=pg ) # type:ignore

    if cnt > 0:
        print( "Indexelés..." )
        VectorDB.reIndex()

    print(f"\nKész! {cnt} oldal beindexelve, {skip} oldal kihagyva.")
    cfg.saveConfig()

if __name__ == "__main__":
    print( "Starting WikiJS Scraper..." )
    main()