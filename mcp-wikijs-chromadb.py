import os
import chromadb # type: ignore
from chromadb.utils import embedding_functions # type: ignore
from mcp.server.fastmcp import FastMCP # type: ignore
import uvicorn # type: ignore
import requests # type: ignore
from configmanager import configmanager as configManager


cfg = configManager( "mcp-config.json" )

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
            host=cfg.get( "chroma_host" ),
            port=cfg.get( "chroma_port" )
        )
        collection = db_client.get_collection(
            name=cfg.get( "collection_name" ), 
            embedding_function=ef
        )
        print(f"Sikeresen csatlakozva a ChromaDB-hez: {cfg.get('chroma_host')}:{cfg.get('chroma_port')}")
    except Exception as e:
        print(f"HIBA: Nem sikerült kapcsolódni a ChromaDB-hez: {e}")
        # Itt érdemes kezelni, ha még nem létezik a collection
        collection = None

    @mcp.tool()
    def search_wiki(query: str, limit: int  = 12) -> str:
        """
        Search in Company Wiki. Use this as your primary source of information about 
        processes, workflows, policies, tools, employee role descriptions, 
        subscriptions and all the other possible internal documentation. This function 
        will return full article for the most relevant result and snippets from 
        other relevant articles. If you got a snipped and you need more information,
        use the 'get_wiki_page' function with the page ID to retrieve the full content
        of that article.
        Put your search string into the 'query' parameter. Always show the URL of the used pages as clicable links.
        You can start up to 6 searches or page downloads to find the most relevant answers.
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

            if ( i == 0 ):
                print( f"Returning page: {meta.get('url', '' )}" )
                clean_doc = get_wiki_page( page_id=int(meta.get('id', '0')) )
            else:
                print( f"Returning snippet from: {meta.get('url', '' )}" )
                clean_doc = doc.replace("passage: ", "", 1)
                print( f"\t{clean_doc[:60]}..." )
            
            formatted_results.append(
                f"--- SOURCE PAGE: {meta.get('title', 'Névtelen')} ---\n"
                f"ID: {meta.get('id', '')}\n"
                f"URL: {meta.get('url', '')}\n"
                f"DESCRIPTION: {meta.get('description', '')}\n"
                f"LAST UPDATED: {meta.get('updatedAt', '')}\n"
                f"RELEVANCE SCORE: {results['distances'][0][i]:.4f}\n"
                f"CONTENT:\n{clean_doc[:35000]}..."
                f"RESULT_TYPE: {"WIKI_SNIPPET" if i > 0 else "FULL_ANSWER"}"
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
              path
            }
          }
        }
        """
        try:
            resp = requests.post(
                cfg.get("wiki_url"), # type: ignore
                json={'query': query, 'variables': {'id': page_id}},
                headers={"Authorization": f"Bearer {cfg.get('wiki_token')}"}
            )
            data = resp.json()['data']['pages']['single']
            print( data.keys() )
            
            if not data:
                return f"Hiba: A {page_id} azonosítójú oldal nem található."

            return (f"TITLE: {data['title']}\n"
                    f"ID: {page_id}\n"
                    f"URL: {cfg.get('wiki_url').replace('/graphql', '')}/{data['path']}\n"
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