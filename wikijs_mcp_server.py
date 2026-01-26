import os
import chromadb # type: ignore
from chromadb.utils import embedding_functions # type: ignore
from mcp.server.fastmcp import FastMCP # type: ignore
import uvicorn # type: ignore
import requests # type: ignore

# --- KONFIGURÁCIÓ ---
# Itt add meg a folyamatosan futó ChromaDB adatait
CHROMA_HOST = "localhost"  # A ChromaDB szerver IP címe
CHROMA_PORT = 7701           # A specifikus port
COLLECTION_NAME = "wiki_pages"
WIKI_URL = "https://wiki.umbrella.tv/graphql"  # A te Wiki.js címed
WIKI_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGkiOjEsImdycCI6MSwiaWF0IjoxNzY4NzQ3NDI3LCJleHAiOjE4NjM0MjAyMjcsImF1ZCI6InVybjp3aWtpLmpzIiwiaXNzIjoidXJuOndpa2kuanMifQ.K_FTVoZRSThtO4eoXjXUzFGM7QJXO_JgVwLeRcpZgNI7IvaDHEiCmz2yWmHMSYtxO4Y2KNcj1XqOL1CtLS7X3HgEOQEBprQhvYuZMqGsIoUrGIcsMJ3FL4X0pioISnlYr6vnt22_FVt9lmCPNW2Pb4UfYIyYSWcBhYpT20iVsWlXhcjv33M_UFYdsfVM3eFe8i475fK6rVFMLq5gWoNPP2BPuao6J5lExJ74qibXcKzFPoCVOw6fOzgNXo8ONyVR2UFrX0ZnJfg4OLoWiM-7WpjNXDz1jgo1yUqLFO06XklRkcZQTilutLjxa3aTmYr3ukxp7W_cD53SsmoHYF28hg"

def create_app():
    mcp = FastMCP(name="WikiMultilingualSearch")

    # 1. Többnyelvű embedding modell beállítása (kliens oldalon fut)
    # Az intfloat/multilingual-e5-small kiváló magyar nyelvhez
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="intfloat/multilingual-e5-small"
    )

    # 2. Csatlakozás a távoli ChromaDB-hez
    try:
        db_client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT
        )
        collection = db_client.get_collection(
            name=COLLECTION_NAME, 
            embedding_function=ef
        )
        print(f"Sikeresen csatlakozva a ChromaDB-hez: {CHROMA_HOST}:{CHROMA_PORT}")
    except Exception as e:
        print(f"HIBA: Nem sikerült kapcsolódni a ChromaDB-hez: {e}")
        # Itt érdemes kezelni, ha még nem létezik a collection
        collection = None

    @mcp.tool()
    def search_wiki(query: str, limit: int  = 4) -> str:
        """
        Semantic search in Company Wiki knowledge base. Treat this as your primary source 
        of information about process documents, policies, tools, workflows, employee role 
        descriptions, subscriptions and all the other possible internal documentation.
        If you find a relevant article, give the user detailed information from it. 
        Put your search string into the 'query' parameter. Always show the URL of the used pages.
        Format all the URL-s a clickable links.
        You can start up to 4 searches or page downloads to find the most relevant answers.
        """
        if collection is None:
            return "Error: Connection to the vector database has been lost."

        print( f"Search: {query}" )
        results = collection.query(
            query_texts=[f"query: {query}"],
            n_results=limit
        )

        if not results['documents'] or not results['documents'][0]:
            print( "Result: NONE" )
            return "No relevant information found in the Wiki."

        formatted_results = []
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i]
            
            # A "passage: " prefixet (ha bent maradt az indexelésnél) itt levághatjuk a szebb megjelenésért
            clean_doc = doc.replace("passage: ", "", 1)
            
            formatted_results.append(
                f"--- SOURCE PAGE: {meta.get('title', 'Névtelen')} ---\n"
                f"ID: {meta.get('id', '')}\n"
                f"URL: {meta.get('url', '')}\n"
                f"DESCRIPTION: {meta.get('description', '')}\n"
                f"LAST UPDATED: {meta.get('updatedAt', '')}\n"
                f"RELEVANCE SCORE: {results['distances'][0][i]:.4f}\n"
                f"CONTENT:\n{clean_doc[:35000]}..."
            )

        return "\n\n" + "\n\n".join(formatted_results)

    @mcp.tool()
    def get_wiki_page(page_id: int) -> str:
        """
        Retrieves the complete content of a specific Wiki page based on its ID.
        Use this when you want to get deeper knowledge about a document after searching.
        Always cite the source of your information with title and URL.
        Put the page ID into the 'page_id' parameter.
        """
        query = """
        query($id: Int!) {
          pages {
            single(id: $id) {
              title
              content
              description
              updatedAt
            }
          }
        }
        """
        try:
            resp = requests.post(
                WIKI_URL,
                json={'query': query, 'variables': {'id': page_id}},
                headers={"Authorization": f"Bearer {WIKI_TOKEN}"}
            )
            print( f'data: {resp.json()}' )
            data = resp.json()['data']['pages']['single']
            
            if not data:
                return f"Hiba: A {page_id} azonosítójú oldal nem található."

            return (f"TITLE: {data['title']}\n"
                    f"ID: {page_id}\n"
                    f"URL: {WIKI_URL}/a/pages/{page_id}\n"
                    f"LAST UPDATED: {data['updatedAt']}\n"
                    f"PAGE DESCRIPTION: {data['description']}\n"
                    f"CONTENT:\n{data['content']}")
            
        except Exception as e:
            print( f"Hiba a Wiki API elérésekor: {str(e)}" )
            return f"Hiba történt a Wiki API elérésekor: {str(e)}"


    return mcp.sse_app()


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=10002 )