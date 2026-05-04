
import time
import lancedb  # type: ignore
from lancedb.embeddings import get_registry # type: ignore
from lancedb.pydantic import LanceModel, Vector # type: ignore
from langchain_text_splitters import MarkdownTextSplitter # type: ignore
from typing import Optional


class Page:
    source: str
    page_id: str
    title: str
    url: str
    description: str
    text: str
    updatedAt: str


class WikiVector:
    def __init__(self, datapath, embedding_model_name, embedding_model_device, collection_name, chunk_size = 1000, chunk_overlap = 200 ):
        self.db = lancedb.connect( datapath )
        self.registry = get_registry().get("sentence-transformers")
        self.model = self.registry.create(name=embedding_model_name, device=embedding_model_device )
        self.table = collection_name
        self.Chunk = self.create_chunk_class()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if self.table in self.db.list_tables().tables:
            self.table = self.db.open_table(self.table)
        else:
            # Ha új, létrehozzuk üresen a sémával
            self.table = self.db.create_table(self.table, schema=self.create_chunk_class() )


    def create_chunk_class( self ):
        model = self.model

        class Chunk( LanceModel ): 
            source: str
            text: str = model.SourceField() # Ezt indexeli a vektoros kereső
            vector: Optional[Vector(model.ndims())] = model.VectorField(default=None) # type: ignore # Automatikus embedding
            page_id: str
            title: str
            url: str
            description: str
            updatedAt: str

        return Chunk


    def search( self, query, query_type="hybrid", limit=5 ):
        return self.table.search( query, query_type=query_type ).limit(limit).to_pydantic(self.Chunk) # type: ignore


    def maintenance( self):
        self.table.create_fts_index( "text", replace=True )   
        print( "Karbantartás..." )
        for i in range(3):
            try:
                self.table.optimize()
                break
            except:
                print( "Concurrency during optimization, retrying..." )
                time.sleep(2)
                pass


    def addPage( self, page ):
        self.table.delete( f"page_id = '{page.page_id}'" )
        text_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
        chunks = text_splitter.split_text( page.text ) # type: ignore
        chunkList = []
        if chunks:
            for c in chunks:
                chunk = self.Chunk(
                    source = page.source,
                    text = f"passage: {page.title}\n\n{c}",
                    page_id = str( page.page_id ),
                    title = page.title,
                    url = page.url,
                    description=page.description,
                    updatedAt=page.updatedAt,
                )
                chunkList.append( chunk )
                
            self.table.add( chunkList )
            self.table.create_fts_index( "text", replace=True )


def __init__():
    pass