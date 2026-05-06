import time

import httplib2
import sys
import io
from configmanager import config as cfg
import kbvector
import gdrive

if __name__ == "__main__":

    lastrun = cfg.get('lastrun')

    cfg.set('lastrun', time.strftime( '%Y-%m-%dT%H:%M:%SZ', time.gmtime() ))

    try:
        with open("knownids.txt", "r") as f:
            ids = f.read().splitlines()
    except FileNotFoundError:
        ids = []

    Drive = gdrive.GDriveClient(service_account_key=cfg.get("service_account_key"), 
                                service_account_user=cfg.get("service_account_user") )
    
    folder_id = cfg.get( "google_drive_root", "" )
    if ( folder_id == "" ):
        print( "Error: No Google Drive folder ID provided in config (google_drive_root)." )
        sys.exit(1)
    

    VectorDB = kbvector.WikiVector( datapath=cfg.get( "lancedb_datapath" ), 
                                     embedding_model_name=cfg.get("embedding_model_name"), 
                                     embedding_model_device=cfg.get("embedding_model_device"), 
                                     collection_name=cfg.get("collection_name"), 
                                     chunk_size=int(cfg.get("chunk_size")), # type: ignore
                                     chunk_overlap=int(cfg.get("chunk_overlap")) ) # type: ignore

    for item in Drive.recursive_list_folder_contents(folder_id):
        meta = Drive.get_file_meta(item)

        if meta.get('mimeType') in gdrive.INDEX_MIME_TYPES and ( meta.get('modifiedTime') > lastrun or item.get('modifiedTime') > lastrun or item.get('id') not in ids ): # type: ignore
            ids.append( item.get('id') ) # type: ignore
            content = Drive.get_file_content(item, exportonly=True)
            if ( content is None ):
                print( "  Unable to get content" )
                continue

            print( "Adding page: " + item.get('name') )
            pg = kbvector.Page()
            pg.source = "googledrive"
            pg.page_id = meta.get('id') # type: ignore
            pg.title = item.get('name') # type: ignore
            pg.url = meta.get('webViewLink') # type: ignore
            pg.text = content # type: ignore
            pg.description = ""
            pg.updatedAt = meta.get('modifiedTime') # type: ignore

            VectorDB.addPage( pg )
        else:
            print( f"Skip page: {item.get('name')}" )

    with open("knownids.txt", "w") as f:
        f.write("\n".join(ids))
