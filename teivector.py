import requests
import pyarrow as pa
import time

#
# schemastring: src:string,url:string,pageId:int,updatedAt:string
#

class TEIVector:

    def __init__(self, db, tei_url, schemastring, model_dims, collection_name, chunk_size = 1000, chunk_overlap = 200, indexPrefix="passage:", searchPrefix="query:"):
        self.db = db
        self.tei_url = tei_url.rstrip("/") + "/embed"
        self.model_dims = model_dims
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.indexPrefix = indexPrefix
        self.searchPrefix = searchPrefix

        fields = [
            pa.field( "vector", pa.list_(pa.float32(), self.model_dims) ),
            pa.field( "text", pa.string() )
        ]
        for s in schemastring.split(","):
            name, typ = s.split(":")
            if name not in [ 'text', 'vector']:
                typ = typ.strip()
                if typ == "string" or typ == "str":
                    fields.append( pa.field( name, pa.string() ) )
                elif typ == "int":
                    fields.append( pa.field( name, pa.int64() ) )
                else:
                    raise ValueError(f"Unsupported type in schema: {typ}")
            else:
                raise ValueError( f"Reserved name: {name}" )
        self.schema = pa.schema( fields )
        self._openTable( collection_name )
        

    def _openTable(self, collection_name):
        if collection_name in self.db.list_tables().tables:
            self.table = self.db.open_table(collection_name)
        else:
            self.table = self.db.create_table(collection_name, schema=self.schema)
            self.reIndex()
    

    def getSchema( self ):
        return self.schema
    

    def getEmbedding( self, text ):
        if isinstance(text, str):
            text = [text]

        response = requests.post( 
            self.tei_url, 
            json={"inputs": text}, 
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()


    def embedAndAdd( self, text, metadata ):
        embedding = self.getEmbedding( self.indexPrefix + text )[0]
        record = {
            "vector": embedding,
            "text": text
        }
        
        record.update(metadata)

        self.table.add( [ record ] )


    def _split_markdown(self, text, chunk_size=1000, chunk_overlap=200):
        """Szupergyors, nulla-importos Markdown daraboló."""
        if not text:
            return []
            
        # Először bekezdésekre szedjük (így nem vágunk ketté mondatokat ha nem muszáj)
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # Ha a jelenlegi darab + az új bekezdés belefér a méretbe
            if len(current_chunk) + len(para) <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # Ha már van benne tartalom, elmentjük
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Új darabot indítunk, az átfedés (overlap) szellemében
                # Kiszámoljuk az előző darab végét az átfedéshez
                if len(para) > chunk_size:
                    # Ha maga a bekezdés nagyobb mint a chunk_size, kénytelenek vagyunk karakterre vágni
                    for i in range(0, len(para), chunk_size - chunk_overlap):
                        chunks.append(para[i:i + chunk_size])
                    current_chunk = ""
                else:
                    # Az átfedés miatt az előző chunk végéből átveszünk valamennyit, ha lehet
                    overlap_text = current_chunk[-chunk_overlap:] if current_chunk else ""
                    current_chunk = (overlap_text + "\n\n" + para).strip() if overlap_text else para
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    
    def longTextAdd( self, text, metadata, idField="page_id"):
        self.table.delete( f"{idField} = '{metadata.get(idField)}'" )
        chunks = self._split_markdown(
            text=text,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        if chunks:
            while len(chunks) > 0:
                batch = []
                for i in range(20):
                    if len( chunks ) > 0:
                        batch.append( self.indexPrefix + chunks.pop() )

                embeddings = self.getEmbedding( batch )

                chunkList = []
                for i, chunk_text in enumerate( batch ):
                    record = {
                        "vector": embeddings[i],
                        "text": chunk_text
                    }
                    record.update( metadata )
                    chunkList.append( record )

                self.table.add( chunkList )


    def reIndex( self ):
        self.table.create_fts_index("text", replace=True)
        print( "Karbantartás..." )
        for i in range(3):
            try:
                self.table.optimize()
                break
            except:
                print( "Concurrency during optimization, retrying..." )
                time.sleep(2)
                pass



    def search( self, query, queryType="hybrid", vector_weight=0.6, limit=5 ):
        queryVector = self.getEmbedding( self.searchPrefix + query )[0]
        if queryType == "hybrid":
            res = self.table.search(query_type="hybrid").vector(queryVector).text(query).limit( limit )
        else:
            res = self.table.search( queryVector ).limit( limit )
        return res.to_list()
