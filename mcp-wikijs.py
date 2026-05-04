import lancedb  # type: ignore
import uvicorn  # type: ignore
from lancedb.embeddings import get_registry # type: ignore
from lancedb.pydantic import LanceModel, Vector # type: ignore
from mcp.server.fastmcp import FastMCP # type: ignore
from configmanager import config as cfg
from wikijsclient import WikiJSClient
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send
from middlewares.tokenauth import TokenAuthMiddleware
import kbvector
import gdrive


def getMarkdown( res ):
    pass

def create_app():
    wiki = WikiJSClient( cfg.get( "wiki_url" ), cfg.get( "wiki_token" ) ) # type: ignore

    mcp = FastMCP(name="WikiHybridSearch")

    VectorDB = kbvector.WikiVector( datapath=cfg.get( "lancedb_datapath" ), 
                                        embedding_model_name=cfg.get("embedding_model_name"), 
                                        embedding_model_device=cfg.get("embedding_model_device"), 
                                        collection_name=cfg.get("collection_name"), 
                                        chunk_size=int(cfg.get("chunk_size")), # type: ignore
                                        chunk_overlap=int(cfg.get("chunk_overlap")) ) # type: ignore

    Drive = gdrive.GDriveClient(service_account_key=cfg.get("service_account_key"), 
                                service_account_user=cfg.get("service_account_user") )


    @mcp.tool()
    def search_knowledge_base(queryhu: str, queryen: str = '', limit: int = 5) -> str:
        """
        Search in Company knowledge base. Ask about processes, workflows, policies, 
        tools, employee role descriptions, subscriptions and all the other
        possible internal documentation.
        """

        print(f"Hybrid Search: {queryhu}")

        queries = []
        if queryhu != "":
            queries.append( f"query: {queryhu}" )
        if queryen != "":
            queries.append( f"query: {queryen}" )
        
        if len(queries) == 0:
            return "Error: No query provided."

        for q in queries:
            print( f" - Sub-query: {q}" )
            results = VectorDB.search( q ) # type: ignore
            if results:
                break;

        if not results:
            print( "No results found." )
            return "No relevant information found in the Wiki."


        formatted_results = ["## Knowledge base search results\n"]

        for i, doc in enumerate(results):
            if i == 0:
                print(f"Returning full page: {doc.url}")
                content = ""
                if  doc.source == "wikijs" :
                    content = wiki.convertToMarkdown(wiki.getPage(int(doc.page_id)))["content"] # type: ignore
                elif doc.source == "googledrive":
                    content = Drive.get_file_content_by_id( doc.page_id )
                res_type = "FULL_ANSWER"
            else:
                print(f"Returning snippet from: {doc.url}")
                content = doc.text[9:1000] + "..." 
                res_type = "SNIPPET"

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
    def get_knowledge_base_page(page_id: str) -> str:
        """
        Retrieves the complete content of a specific Wiki page based on its ID.
        Use this when you want to get deeper knowledge about a document after searching.
        Always cite the source of your information with title and URL.
        Put the page ID into the 'page_id' parameter.
        """
        if ( page_id.isnumeric() ):
            page = wiki.convertToMarkdown(wiki.getPage(int(page_id))) 
        else:
            page = Drive.get_file_content_by_id(page_id)

        if not page:
            return f"Error: Page with ID {page_id} not found."

        return "%s%s%s%s%s%s" % ( f"### TITLE: {page['title']}\n" # type: ignore
            f"ID: {page_id}\n"
            f"URL: {page.url}\n" # type: ignore
            f"LAST UPDATED: {page['updatedAt']}\n" # type: ignore
            f"PAGE DESCRIPTION: {page['description']}\n" # type: ignore
            f"CONTENT:\n{page['content']}" ) #  type: ignore

    class AllowAllMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            if scope["type"] in  ( "http", "websocket" ):
                headers = []
                for key, value in scope["headers"]:
                    if key == b"host":
                        headers.append((b"host", b"localhost"))
                    else:
                        headers.append((key, value))
                scope["headers"] = headers
            
            await self.app(scope, receive, send)

    mcp.settings.transport_security.enable_dns_rebinding_protection = False # type: ignore
    app = mcp.streamable_http_app()

    app.add_middleware( AllowAllMiddleware )
    app.add_middleware(
        CORSMiddleware, 
        allow_origins=["*"], 
        allow_methods=["*"], 
        allow_headers=["*"]
    )
    app.add_middleware( TokenAuthMiddleware )

    return app


if __name__ == "__main__":
    app = create_app()        
    uvicorn.run(app, host=str(cfg.get( 'listenaddress', '0.0.0.0' )), port=int( cfg.get( 'listenport', 10002 ) ) ) # type: ignore
