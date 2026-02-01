import os
import sys
import lancedb  # type: ignore
import requests # type: ignore
import uvicorn  # type: ignore
from lancedb.embeddings import get_registry # type: ignore
from lancedb.pydantic import LanceModel, Vector # type: ignore
from mcp.server.fastmcp import FastMCP # type: ignore
from configmanager import configmanager as configManager
import subprocess
from wikijsclient import WikiJSClient

cfg = configManager( "mcp-config.json" )


def create_app():
    wiki = WikiJSClient( cfg.get( "wiki_url" ), cfg.get( "wiki_token" ) )

    mcp = FastMCP(name="WikiHybridSearch")

    db = lancedb.connect( cfg.get( "lancedb_datapath" ) )
    registry = get_registry().get("sentence-transformers")
    #model = registry.create(name="intfloat/multilingual-e5-small", device="cpu")
    model = registry.create(name=cfg.get("embedding_model_name"), device=cfg.get("embedding_model_device"))

    class WikiPage(LanceModel):
        text: str = model.SourceField() # Ezt indexeli a vektoros kereső
        vector: Vector(model.ndims()) = model.VectorField() # type: ignore # Automatikus embedding
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


    @mcp.tool()
    def search_wiki(queryhu: str, queryen: str, limit: int  = 5) -> str:
        """
        Search in Company Wiki using HYBRID search (Semantic + Keyword).
        Returns full article for the top result and snippets for others.
        Use this as your primary source of information about processes, 
        workflows, policies, tools, employee role descriptions, subscriptions
        and all the other possible internal documentation.
        Put the query string into the 'queryhu' parameter in Hungarian
        and into the 'queryen' parameter in English.
        Always show the URL of the used pages as clickable links.
        You can start up to 6 searches or page downloads to find the most relevant answers."""
        if table is None:
            return "Error: Local database is not initialized."

        print(f"Hybrid Search: {queryhu}")

        queries = [ f"query: {queryhu}", f"query: {queryen}" ]
        for q in queries:
            print( f" - Sub-query: {q}" )
            results = table.search( q, query_type="hybrid" ) \
                        .limit(limit) \
                        .to_pydantic(WikiPage)
            if results:
                break;

        if not results:
            print( "No results found." )
            return "No relevant information found in the Wiki."


        formatted_results = ["## Wiki Search Results\n"]

        for i, doc in enumerate(results):
            if i == 0:
                print(f"Returning full page: {doc.url}")
                content = wiki.convertToMarkdown(wiki.getPage(doc.page_id))["content"]
                res_type = "FULL_ANSWER"
            else:
                print(f"Returning snippet from: {doc.url}")
                content = doc.text[:1000] + "..." 
                res_type = "WIKI_SNIPPET"

            formatted_results.append(
                f"### TITLE: {doc.title}\n"
                f"- **ID:** {doc.page_id}\n"
                f"- **URL:** {doc.url}\n"
                f"- **UPDATED:** {doc.updatedAt}\n"
                f"- **RESPONSETYPE:** {res_type}\n\n"
                f"**CONTENT:**\n{content}\n"
            )

        return "\n\n---\n\n".join(formatted_results)


    @mcp.tool()
    def get_wiki_page(page_id: int) -> str:
        """
        Retrieves the complete content of a specific Wiki page based on its ID.
        Use this when you want to get deeper knowledge about a document after searching.
        Always cite the source of your information with title and URL.
        Put the page ID into the 'page_id' parameter.
        """
        page = wiki.convertToMarkdown(wiki.getPage(page_id))

        if not page:
            return f"Error: Page with ID {page_id} not found."

        return (f"### TITLE: {page['title']}\n"
                f"ID: {page_id}\n"
                f"URL: {cfg.get('wiki_url').replace('/graphql', '')}/{page['locale']}/{page['path']}\n" # type: ignore
                f"LAST UPDATED: {page['updatedAt']}\n"
                f"PAGE DESCRIPTION: {page['description']}\n"
                f"CONTENT:\n{page['content']}")
            

    app = mcp.sse_app()


#    @app.post("/ingest")
#    async def ingest_wiki_page(page: WikiPage):
#        """Ezt hívhatja a külső script, hogy adatot toljon be."""
#        table.add([page])
#        # FTS index frissítése minden betöltés után (vagy időzítve)
#        table.create_fts_index("text", replace=True)
#        return {"status": "ok"}


    return app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=10002 )