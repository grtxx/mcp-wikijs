import requests
import subprocess
import re

class WikiJSClient:

    def __init__(self, wiki_url: str, wiki_token: str):
        self.wiki_url = wiki_url
        self.wiki_token = wiki_token


    def convertToMarkdown( self, page ):
        if page is None:
            return None
        if ( page["contentType"] != "markdown" ):
            try:
                page["content"] = re.sub( r'\<(\/?)figure[^\>]*\>', '', page["content"] )
                result = subprocess.run(['pandoc', '-f', 'html', '-t', 'markdown'], 
                    input=page["content"], text=True, capture_output=True, check=True)
                page["content"] = result.stdout
                page['content'] = page['content'].replace('\r\n', '\n').strip()
                page["contentType"] = "markdown"
            except subprocess.CalledProcessError:
                return None
        
        return page


    def getPage( self, page_id: int ):
        """
        Retrieves the complete content of a specific Wiki page based on its ID.
        """

        query = """
        query($id: Int!) {
          pages {
            single(id: $id) {
              title
              content
              description
              updatedAt
              path,
              contentType,
              locale
            }
          }
        }
        """
        
        try:
            resp = requests.post( self.wiki_url, json={'query': query, 'variables': {'id': page_id} }, headers={"Authorization": f"Bearer {self.wiki_token}"} )
            page = resp.json()['data']['pages']['single']
            return page
        except Exception as e:
            print( f"Wiki API error: {str(e)}" )
            return None


    def get_all_pages( self ):
        """Lekéri az összes elérhető oldal listáját (id, path, title)."""
        query = """
        {
        pages {
            list { id, path, title, updatedAt, createdAt }
        }
        }
        """
        response = requests.post( self.wiki_url, 
                                json={'query': query}, 
                                headers={"Authorization": f"Bearer {self.wiki_token}"})
        return response.json()['data']['pages']['list']
