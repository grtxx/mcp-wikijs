#!/opt/MAINCHAT/venv/bin/python3

import asyncio
import os
import sys
import httpx
from mcp.server.fastmcp import FastMCP
import uvicorn




def create_app():

    mcp = FastMCP( name="WikiJS-MCP" )

    WIKI_URL = "https://wiki.umbrella.tv/graphql"
    WIKI_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGkiOjEsImdycCI6MSwiaWF0IjoxNzY4NzQ3NDI3LCJleHAiOjE4NjM0MjAyMjcsImF1ZCI6InVybjp3aWtpLmpzIiwiaXNzIjoidXJuOndpa2kuanMifQ.K_FTVoZRSThtO4eoXjXUzFGM7QJXO_JgVwLeRcpZgNI7IvaDHEiCmz2yWmHMSYtxO4Y2KNcj1XqOL1CtLS7X3HgEOQEBprQhvYuZMqGsIoUrGIcsMJ3FL4X0pioISnlYr6vnt22_FVt9lmCPNW2Pb4UfYIyYSWcBhYpT20iVsWlXhcjv33M_UFYdsfVM3eFe8i475fK6rVFMLq5gWoNPP2BPuao6J5lExJ74qibXcKzFPoCVOw6fOzgNXo8ONyVR2UFrX0ZnJfg4OLoWiM-7WpjNXDz1jgo1yUqLFO06XklRkcZQTilutLjxa3aTmYr3ukxp7W_cD53SsmoHYF28hg"

    async def query_wiki(query: str, variables: dict = None): # type: ignore
        headers = {"Authorization": f"Bearer {WIKI_TOKEN}"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WIKI_URL, 
                json={"query": query, "variables": variables or {}}, 
                headers=headers
            )
            return response.json()

    @mcp.tool()
    async def search_wiki(keyword: str) -> str:
        """
        Search in Wiki.js content based on a keyword. Use this tool for primary knowledge base lookups. 
        Always provide detailed information from the wiki pages in your response.
        """
        query = """
        query($term: String!) {
        pages {
            search(query: $term) {
            results { id, title, description, path, locale }
            }
        }
        }
        """
        data = await query_wiki(query, {"term": keyword})
        results = data.get("data", {}).get("pages", {}).get("search", {}).get("results", [])
        print( f"Search results for '{keyword}':\n{results}\n\n" )
        print( f"Full data: \n{data}\n\n" )
        if not results:
            return "No results found in the wiki."
        
        output = "Results in the Wiki:\n"
        for r in results:
            output += f"- {r['title']} (ID: {r['id']}): {r['description']}\n"
        return output

    @mcp.tool()
    async def get_wiki_page(id: int) -> str:
        """
        Retrieve the content of a specific wiki page based on the id. Always append the page link to your summary.
        """
        print( f"Getting wiki page: {id}" )
        query = """
        query($id: Int!) {
        pages {
            single( id: $id ) {
                title, description, content
            }
        }
        }
        """
        data = await query_wiki(query, {"id": id})
        page = data.get("data", {}).get("pages", {}).get("single")
        print( f"Page data: {page}" )
        if not page:
            return "The page was not found."
        
        return f"Title: {page['title']}\nDescription: {page['description']}\n\nContent:\n{page['content']}"


#    print( asyncio.run( get_wiki_page( "artificial-intelligence/tools") ) )
#    sys.exit()

    return mcp.sse_app()


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10002 )