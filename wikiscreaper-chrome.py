import sys
import time
from chromadb.utils import embedding_functions # type: ignore
import chromadb # type: ignore
import requests # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore
from configmanager import configmanager


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
        list { id, path, title, updatedAt, createdAt }
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

def chunking(raw_text, splitter, id):
    texts = splitter.split_text(raw_text)
    prefixed_chunks = [f"passage: {t}" for t in texts]
    ids = []
    cnt = 0
    for t in texts:
        ids.append(f"WIKIJS-{id}-{cnt}")
        cnt += 1
        if len(t) > 1000:
            print(f"Figyelem: Egy darab szöveg túl hosszú maradt ({len(t)} karakter) az oldal ID {id} esetén.")            
    return prefixed_chunks, ids


def main():
    config = configmanager( "screaper-config.json" )
    lastrun = config.get('lastrun')

    config.set('lastrun', time.strftime( '%Y-%m-%dT%H:%M:%SZ', time.gmtime() ))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    print("Oldalak listázása...")
    pages = get_all_pages()
    
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

        url = f"{WIKI_URL.rstrip('/graphql')}/{path}"
        
        details = get_page_details(int(page_id))
        content = details['content'].replace('\r\n', '\n').strip()
        chunks,ids  = chunking(content, splitter, p['id'])
        
        collection.add(
            documents=chunks,
            metadatas=[ { "title": title, "path": path, "id": page_id, "url": url } ]*len(chunks),
            ids=ids
        )

    print(f"\nKész! {cnt} oldal beindexelve, {skip} oldal kihagyva.")
    config.saveConfig()

if __name__ == "__main__":
    main()