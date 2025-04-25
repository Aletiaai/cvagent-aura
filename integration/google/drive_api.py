# integration/google/drive_api.py 
import io
import os.path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import os
import google.auth # Use the main google-auth library
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError # Good to import for error handling

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/drive'
    ]

# --- Service Account Authentication ---
# Load the service account key path from an environment variable
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

def get_google_api_credentials():
    """
    Authenticates using a Service Account suitable for Cloud Run.

    Returns:
        google.oauth2.service_account.Credentials: The authenticated credentials object.

    Raises:
        Exception: If credentials cannot be loaded (e.g., file not found, invalid format).
    """
    if not SERVICE_ACCOUNT_FILE:
        raise ValueError(
            "Environment variable 'GOOGLE_APPLICATION_CREDENTIALS' is not set. "
            "Provide the path to your service account key file."
        )
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
         raise FileNotFoundError(
            f"Service account key file not found at path: {SERVICE_ACCOUNT_FILE}. "
            "Ensure the file exists and the path is correct."
        )

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        print(f"Successfully loaded service account credentials for scopes: {SCOPES}")
        return creds
    except Exception as e:
        print(f"Error loading service account credentials from {SERVICE_ACCOUNT_FILE}: {e}")
        raise # Re-raise the exception after logging

def build_google_service(service_name: str, version: str, credentials):
    """
    Builds a Google API service client.

    Args:
        service_name (str): The name of the service (e.g., 'drive', 'docs').
        version (str): The version of the service (e.g., 'v3', 'v1').
        credentials: The authenticated credentials object.

    Returns:
        googleapiclient.discovery.Resource: The built service object.

    Raises:
        HttpError: If the service build fails.
    """
    try:
        service = build(service_name, version, credentials=credentials, cache_discovery=False) # cache_discovery=False can help avoid issues in some environments
        print(f"Successfully built Google API service: {service_name} v{version}")
        return service
    except HttpError as error:
        print(f"An error occurred building the {service_name} service: {error}")
        raise # Re-raise the exception


"""def authenticate_drive_api():
    #Authenticates the user for Google Drive API access and returns the service object
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port = 0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials = creds)

def get_folder_id(folder_path):
    #Gets the ID of a folder by its full path in Google Drive.Args: Folder_path: The path to the folder (e.g., "Parent Folder/Subfolder/Target Folder"). Returns: The ID of the target folder (or None if not found).

    parent_id = 'root'  # Start at the root of the Drive
    folder_names = folder_path.split('/')

    for folder_name in folder_names:
        try:
            query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            results = service.files().list(
                q=query,
                fields="files(id)"
            ).execute()
            items = results.get('files', [])
            if not items:
                print(f"Could not find folder: {folder_name}")
                return None  # Folder not found at this level
            parent_id = items[0]['id']  # Update parent_id for the next level
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    return parent_id  # This is the ID of the final folder in the path
    
def list_files_in_folder(folder_id):
    #Lists the files in a given folder. Args: Folder_id: The ID of the folder. Returns: A list of file objects (or [] if an error occurs).
    try:
        results = service.files().list(
            q = f"'{folder_id}' in parents",
            fields = "files(id, name)"
        ).execute()
        items = results.get('files', [])
        return items
    except HttpError as e:
        print(f"An error in listing the files in folder ocurred: {e}")
        return []

def download_file(file_id, file_name, download_dir = "data/resumes"):
    #Downloads a file from Google Drive. Args: file_id: The ID of the file to download. file_name: The name of the file. download_dir: The directory to save the file to.
    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        request = service.files().get_media(fileId = file_id)
        file_path = os.path.join(download_dir, file_name)

        with io.FileIO(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        print(f"file '{file_name}' downloaded to '{file_path}'")
    except HttpError as e:
        print(f"An error occurren while downloading the file {file_name}: {e}")

def number_files_in_drive(drive_folder_id):
    try:
        files = list_files_in_folder(drive_folder_id)
        if not files:
            print("No files found in the Google Drive folder.")

        total_files = len(files)
        return files, total_files
    
    except Exception as e:
            print(f"An error occurred when processing de number of files at folder id: {drive_folder_id} from Drive: {str(e)}")
            return None
    
# Changes: Ensure consistent use of the service object. You might want to make this a class GoogleDriveClient that gets initialized with credentials and holds the service object. Ensure correct import paths for googleapiclient, etc.
"""

