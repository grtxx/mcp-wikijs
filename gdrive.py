import httplib2
import io
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build # type: ignore
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document':     'text/markdown',
    'application/vnd.google-apps.spreadsheet':  'text/markdown',
    'application/vnd.google-apps.presentation': 'text/markdown',
}

INDEX_MIME_TYPES = EXPORT_MIME_TYPES.keys()


class GDriveClient:

    def __init__( self, service_account_key, service_account_user ):
        self.service_account_key = service_account_key
        self.service_account_user = service_account_user
        self.service = self.get_drive_service()


    def get_google_credentials( self, scopes ):
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.service_account_key, scopes)
        creds = creds.create_delegated( self.service_account_user)
        return creds


    def get_drive_service( self ):
        http_auth = self.get_google_credentials(scopes=["https://www.googleapis.com/auth/drive.readonly"]).authorize(httplib2.Http())
        service = build('drive', 'v3', http=http_auth)
        return service


    def list_folder_contents( self, folder_id, page_size=100):
        if ( folder_id == "" ):
            corpora = "user"
        else:
            corpora = "allDrives"

        query = f"'{folder_id}' in parents and trashed = false"
        response = self.service.files().list(
            q=query,
            corpora=corpora,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        return response.get('files', [])


    def list_folder_contents_all( self, folder_id, page_size=100 ):
        items = []
        page_token = None
        while True:
            response = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)",
                pageToken=page_token
            ).execute()
            items.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return items


    def recursive_list_folder_contents(self, folder_id):
        stack = [ folder_id ]
        
        while len(stack)>0:
            current_folder_id = stack.pop()
            items = self.list_folder_contents_all(current_folder_id)
            for item in items:
                if item.get('mimeType') == 'application/vnd.google-apps.folder':
                    stack.append(item.get('id'))
                else:
                    yield item


    def resolveShortcut( self, file ):
        file_id = file.get('id')
        while ( file.get('mimeType') == 'application/vnd.google-apps.shortcut' ):
            file_meta = self.service.files().get(
                fileId=file_id,
                fields='shortcutDetails, modifiedTime, webViewLink',
                supportsAllDrives=True
            ).execute()
            file = {
                'id':file_meta.get('shortcutDetails', {}).get('targetId'),
                'mimeType': file_meta.get('shortcutDetails', {}).get('targetMimeType'),
                'modifiedTime': file_meta.get('modifiedTime'),
                'webViewLink': file_meta.get('webViewLink')
            }
        return file

    def get_file_meta( self, file ):
        file = self.resolveShortcut(file)
        return file



    def get_file_content( self, file, exportonly = False ) -> str | None:
        file = self.resolveShortcut(file)
        if not 'id' in file:
            return None
            
        export_mime = EXPORT_MIME_TYPES.get( file['mimeType'] )

        if ( export_mime is None ):  
            if ( exportonly ):
                return None
            request = self.service.files().get_media(fileId=file['id'], supportsAllDrives=True)
        else:
            request = self.service.files().export_media( fileId=file['id'], mimeType=export_mime )        
        fl = io.BytesIO()
        downloader = MediaIoBaseDownload(fl, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fl.getvalue().decode('utf-8')
    

    def get_file_content_by_id( self, file_id, exportonly = False ) -> str | None:
        file = self.service.files().get( fileId=file_id, fields='id, mimeType, modifiedTime, webViewLink', supportsAllDrives=True ).execute()
        return self.get_file_content( file, exportonly=exportonly )


def __init__():
    pass
