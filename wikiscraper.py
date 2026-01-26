from chromadb.utils import embedding_functions # type: ignore
import chromadb # type: ignore
import requests # type: ignore

# --- BEÁLLÍTÁSOK ---
WIKI_URL = "https://wiki.umbrella.tv/graphql"  # A te Wiki.js címed
WIKI_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGkiOjEsImdycCI6MSwiaWF0IjoxNzY4NzQ3NDI3LCJleHAiOjE4NjM0MjAyMjcsImF1ZCI6InVybjp3aWtpLmpzIiwiaXNzIjoidXJuOndpa2kuanMifQ.K_FTVoZRSThtO4eoXjXUzFGM7QJXO_JgVwLeRcpZgNI7IvaDHEiCmz2yWmHMSYtxO4Y2KNcj1XqOL1CtLS7X3HgEOQEBprQhvYuZMqGsIoUrGIcsMJ3FL4X0pioISnlYr6vnt22_FVt9lmCPNW2Pb4UfYIyYSWcBhYpT20iVsWlXhcjv33M_UFYdsfVM3eFe8i475fK6rVFMLq5gWoNPP2BPuao6J5lExJ74qibXcKzFPoCVOw6fOzgNXo8ONyVR2UFrX0ZnJfg4OLoWiM-7WpjNXDz1jgo1yUqLFO06XklRkcZQTilutLjxa3aTmYr3ukxp7W_cD53SsmoHYF28hg"

# 1. ChromaDB inicializálása (alapértelmezett helyi embedding-gel)
# Ez letölt egy kisméretű modellt, ami helyben futtatja a vektorizálást (ingyen van)
huggingface_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="intfloat/multilingual-e5-small"
)
client = chromadb.HttpClient( host="localhost", port=7701 )
collection = client.get_or_create_collection(
        name="wiki_pages", 
        embedding_function=huggingface_ef)

def get_all_pages():
    """Lekéri az összes elérhető oldal listáját (id, path, title)."""
    query = """
    {
      pages {
        list { id, path, title }
      }
    }
    """
    response = requests.post(WIKI_URL, 
                             json={'query': query}, 
                             headers={"Authorization": f"Bearer {WIKI_TOKEN}"})
    return response.json()['data']['pages']['list']

def get_page_details(page_id):
    """Lekéri egy konkrét oldal tartalmát."""
    query = """
    query($id: Int!) {
      pages {
        single(id: $id) { content, title, description }
      }
    }
    """
    response = requests.post(WIKI_URL, 
                             json={'query': query, 'variables': {'id': page_id}},
                             headers={"Authorization": f"Bearer {WIKI_TOKEN}"})
    return response.json()['data']['pages']['single']


def main():
    print("Oldalak listázása...")
    pages = get_all_pages()
    
    for p in pages:
        page_id = p['id']
        title = p['title']
        path = p['path']
        url = f"{WIKI_URL.rstrip('/graphql')}/{path}"
        
        print(f"Feldolgozás: {title} ({path})...")
        details = get_page_details(int(page_id))
        content = details['content']
        
        # Ha túl hosszú a cikk, érdemes lehetne feldarabolni (chunking), 
        # de kezdésnek egyben is jó lesz a ChromaDB-nek.
        collection.add(
            documents=[content],
            metadatas=[ { "title": title, "path": path, "id": page_id, "url": url } ],
            ids=str(page_id)
        )

    print(f"\nKész! {len(pages)} oldal beindexelve a 'wiki_pages' kollekcióba.")

if __name__ == "__main__":
    main()