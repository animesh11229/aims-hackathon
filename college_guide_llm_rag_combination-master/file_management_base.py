import os.path
import io
import sys
from docx import Document
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader
import mimetypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# If modifying these scopes, delete the file token.json.
# We need the full 'drive' scope to be able to change file permissions.
SCOPES = ["https://www.googleapis.com/auth/drive"]

# --- IMPORTANT ---
# Set the ID of the folder you want to list for the hierarchy view.
# Use 'root' to start from your main "My Drive" directory.

TARGET_FOLDER_NAME =  "NSUT_MAIN"
TARGET_FOLDER_ID = ""


def extract_text_from_file(raw_data: bytes, filename: str) -> str:
    """
    Extracts plain text from raw byte data of a file.

    This function supports .pdf, .docx, and .txt files. It determines the
    file type from the filename's extension and uses the appropriate library
    to extract the text content.

    Args:
        raw_data: The raw content of the file as a bytes object.
        filename: The original name of the file (e.g., "my_syllabus.pdf").

    Returns:
        A string containing the extracted text, or an error message if the
        file type is unsupported or an error occurs during processing.
    """
    # Get the file extension to determine the file type
    # os.path.splitext is a safe way to get the extension
    _, extension = os.path.splitext(filename)
    extension = extension.lower()

    text_content = ""

    try:
        if extension == '.pdf':
            # Use io.BytesIO to treat the raw byte data like a file
            pdf_file = io.BytesIO(raw_data)
            reader = PdfReader(pdf_file)
            # Loop through all pages and concatenate their text
            for page in reader.pages:
                # Add 'or ""' to handle pages with no extractable text
                text_content += page.extract_text() or ""

        elif extension == '.docx':
            # python-docx can also read from a file-like object
            docx_file = io.BytesIO(raw_data)
            document = Document(docx_file)
            # Join the text from all paragraphs
            all_paragraphs = [p.text for p in document.paragraphs]
            text_content = "\n".join(all_paragraphs)


        elif extension in ['.txt', '.json']:

            # For text-based files like txt and json, just decode the bytes

            # into a string using the common UTF-8 encoding.

            text_content = raw_data.decode('utf-8')

        else:
            return f"Error: Unsupported file type '{extension}'. This function only supports .pdf, .docx, and .txt files."

    except Exception as e:
        # Catch potential errors during file processing
        return f"Error processing file '{filename}': {e}"

    return text_content


def download_file_content(service, file_id):
    """
    Downloads a file's content from Google Drive.

    Args:
        service: The authenticated Google Drive API service object.
        file_id (str): The ID of the file to download.

    Returns:
        bytes: The content of the file as bytes, or None if an error occurs.
    """
    try:
        # Prepare the request to get the file's media content.
        request = service.files().get_media(fileId=file_id)

        # Use an in-memory binary stream to hold the downloaded data.
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        print("Downloading file content...")
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")

        print("✅ Download complete.")
        # Return the downloaded content by getting the value from the BytesIO buffer.
        return fh.getvalue()

    except HttpError as error:
        print(f"An error occurred while downloading the file: {error}")
        return None


def create_sharable_link(service, file_id):
    """
    Creates a public, shareable link for a file.

    Args:
        service: The authenticated Google Drive API service object.
        file_id (str): The ID of the file to share.

    Returns:
        str: The public webViewLink for the file, or None if an error occurs.
    """
    try:
        # Define the permission to make the file public for anyone with the link.
        permission = {"type": "anyone", "role": "reader"}

        # Create the permission.
        service.permissions().create(fileId=file_id, body=permission).execute()

        # Get the file's metadata again to retrieve the shareable link.
        # We request the 'webViewLink' field which contains the URL.
        file_metadata = service.files().get(fileId=file_id, fields="webViewLink").execute()

        print("✅ Sharable link created successfully.")
        return file_metadata.get("webViewLink")

    except HttpError as error:
        print(f"An error occurred while creating the sharable link: {error}")
        return None


def get_file_id_from_path(service, file_path: str) -> str | None:
    """
    Finds the ID of a file or folder in Google Drive from its full path.

    Args:
        service: An authenticated Google Drive API v3 service object.
        file_path: The full path of the file, e.g., "FolderA/SubfolderB/file.txt".

    Returns:
        The file ID as a string, or None if the path is not found.
    """
    if not service or not file_path:
        return None

    # Split the path into its components
    path_parts = file_path.strip("/").split("/")

    # Start traversal from the root folder
    parent_id = TARGET_FOLDER_ID

    # Traverse through the folders in the path
    for part in path_parts:
        query = (
            f"name = '{part}' and "
            f"'{parent_id}' in parents and "
            f"trashed = false"
        )

        try:
            # Search for the current part (file or folder) in the parent folder
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                corpora='user'  # Or 'allDrives' if searching in Shared Drives
            ).execute()

            items = response.get('files', [])

            if not items:
                print(f"Error: Path part '{part}' not found in parent ID '{parent_id}'.")
                return None

            # Get the ID of the found item for the next iteration
            found_item = items[0]
            parent_id = found_item['id']

        except Exception as e:
            print(f"An API error occurred: {e}")
            return None

    # The final 'parent_id' is the ID of the requested file/folder
    return parent_id




def get_file_by_path(service, file_path, start_folder_name=TARGET_FOLDER_NAME):
    if start_folder_name !=None or len(start_folder_name) != 0:
        start_folder_id = TARGET_FOLDER_ID
    """
    Finds a file or folder in Google Drive by its path.

    Args:
        service: The authenticated Google Drive API service object.
        file_path (str): The path to the file, e.g., "folder/subfolder/file.txt".
        start_folder_id (str): The ID of the folder to start the search from.
                               Defaults to 'root'.

    Returns:
        dict: The file object if found, otherwise None.
    """
    # Clean up the path and split it into individual components
    path_parts = [part for part in file_path.split("/") if part]
    if not path_parts:
        print("Error: The file path is empty.")
        return None

    current_folder_id = start_folder_id

    # Traverse the path component by component
    for i, part in enumerate(path_parts):
        is_last_part = i == len(path_parts) - 1

        # Determine if we are looking for a file or a folder
        if is_last_part:
            mime_type_query = "mimeType != 'application/vnd.google-apps.folder'"
        else:
            mime_type_query = "mimeType = 'application/vnd.google-apps.folder'"

        try:
            # Correctly escape single quotes in the file/folder name for the query.
            escaped_part = part.replace("'", "\\'")
            query = (
                f"'{current_folder_id}' in parents and "
                f"name = '{escaped_part}' and "
                f"{mime_type_query} and "
                f"trashed = false"
            )

            results = (
                service.files()
                .list(
                    q=query,
                    pageSize=2,
                    fields="files(id, name)",
                )
                .execute()
            )
            items = results.get("files", [])

            if not items:
                print(f"Error: Could not find '{part}' in the path.")
                return None
            if len(items) > 1:
                print(f"Error: Ambiguous path. Found multiple items named '{part}'.")
                return None

            found_item = items[0]
            if is_last_part:
                print("✅ File found!")
                return found_item
            else:
                current_folder_id = found_item["id"]

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    return None


def list_items_recursively(service, folder_id, indent="",f=sys.stdout):
    """
    Recursively lists files and folders in a given folder, creating a tree view.
    """
    page_token = None
    while True:
        try:
            results = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )
            items = results.get("files", [])

            for item in items:
                print(f"{indent}├── {item['name']}",file=f)
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    list_items_recursively(service, item["id"], indent + "    ",f)

            page_token = results.get("nextPageToken", None)
            if page_token is None:
                break

        except HttpError as error:
            print(f"An error occurred while listing folder {folder_id}: {error}")
            break


def get_upload_ready_file_for_llm(file_name, file_content):
    """
    Sends a file and a prompt to the Gemini API using the Python SDK.

    Args:
        file_name (str): The original name of the file (e.g., "my_doc.pdf").
        file_content (bytes): The raw byte content of the file.

    Returns:
        content ready file
    """
    # Step 1: Guess the file's MIME type from its name.
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type is None:
        mime_type = "application/octet-stream"  # A generic default

    # Step 2: Create the file part for the prompt.
    # The SDK handles the encoding. You just provide the raw bytes and MIME type.
    file_part = {
        "file_name": file_name,
        "mime_type": mime_type,
        "data": extract_text_from_file(file_content,filename=file_name)
    }
    return file_part
'''development stage auth'''
# def authenticate_and_return_service():
#     """Shows basic usage of the Drive v3 API."""
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             # If you changed the SCOPES, you must delete token.json for this to work.
#             print("A browser window will open for you to authorize this script.")
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 "credentials.json", SCOPES
#             )
#             creds = flow.run_local_server(port=0)
#         with open("token.json", "w") as token:
#             token.write(creds.to_json())
#
#     try:
#         service = build("drive", "v3", credentials=creds)
#         return service,creds
#     except HttpError as error:
#         print(f"An error occurred: {error}")

'''production stage auth'''
def authenticate_and_return_service():
    global TARGET_FOLDER_ID
    """Authenticates the service account and returns the Drive service."""

    # The path to your service account key file
    SERVICE_ACCOUNT_FILE = 'service_account.json'

    # The scopes required by the application
    SCOPES = ['https://www.googleapis.com/auth/drive']

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        service = build('drive', 'v3', credentials=creds)
        print("✅ Authentication successful.")
        TARGET_FOLDER_ID = find_shared_folder_id(service,TARGET_FOLDER_NAME)
        return service

    except FileNotFoundError:
        print(f"❌ Error: The service account key file was not found at '{SERVICE_ACCOUNT_FILE}'.")
        return None
    except Exception as e:
        print(f"An error occurred during authentication: {e}")
        return None


def get_file_name_from_id(service, file_id: str) -> str:
    """
    Retrieves the name of a file in Google Drive using its ID.

    Args:
        service: An authenticated Google Drive API service object.
        file_id: The ID of the file.

    Returns:
        The name of the file as a string, or an error message.
    """
    try:
        # Call the Drive v3 API's files().get() method
        # 'fields="name"' tells the API to only return the file's name
        file_metadata = service.files().get(fileId=file_id, fields='name').execute()

        # The result is a dictionary, e.g., {'name': 'My Document.docx'}
        return file_metadata.get('name')

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def find_shared_folder_id(service, folder_name: str) -> str | None:
    """
    Finds the ID of a folder shared with the service account.

    This function searches everywhere the service account has access,
    not just within its own 'root' drive.

    Args:
        service: An authenticated Google Drive API v3 service object.
        folder_name: The name of the shared folder to find.

    Returns:
        The folder ID as a string, or None if not found.
    """
    print(f"Searching for shared folder: '{folder_name}'...")
    try:
        # Note: We are NOT specifying 'parents' in the query.
        # This searches all folders the service account can access.
        query = (
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            # Use corpora='allDrives' and includeItemsFromAllDrives=True
            # to be thorough, especially if dealing with Shared Drives.
            corpora='allDrives',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()

        items = response.get('files', [])

        if not items:
            print(f"❌ Error: Shared folder '{folder_name}' not found.")
            return None
        if len(items) > 1:
            print(f"⚠️ Warning: Found multiple folders named '{folder_name}'. Using the first one.")

        folder_id = items[0]['id']
        print(f"✅ Found shared folder '{folder_name}' with ID: {folder_id}")
        return folder_id

    except HttpError as e:
        print(f"An API error occurred while searching for shared folder: {e}")
        return None


def list_files_with_full_path(service, folder_id, f=sys.stdout):
    """
    Recursively lists all files with their full paths from within the subfolders
    of a starting folder ID.

    Args:
        service: An authenticated Google Drive API service object.
        folder_id (str): The ID of the folder whose sub-contents are to be listed.
        f (file, optional): A file-like object to write the output to.
                            Defaults to sys.stdout (the console).
    """

    # This helper function will handle the recursion
    def _list_recursively(current_folder_id, current_path):
        """
        Helper function to traverse folders and print file paths.

        Args:
            current_folder_id (str): The ID of the folder currently being processed.
            current_path (str): The path built so far to the current folder.
        """
        try:
            # Query to get all items (files and folders) in the current folder
            query = f"'{current_folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query,
                pageSize=1000,  # Get up to 1000 items at a time
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()

            items = results.get('files', [])

            if not items:
                return

            for item in items:
                item_name = item.get('name')
                item_id = item.get('id')
                mime_type = item.get('mimeType')

                # Construct the full path for the current item
                # If current_path is empty, don't add a leading '/'
                new_path = f"{current_path}/{item_name}" if current_path else item_name

                # If the item is a folder, make a recursive call
                if mime_type == 'application/vnd.google-apps.folder':
                    _list_recursively(item_id,
                                      new_path)
                else:
                    # If it's a file, print its full path
                    print(new_path, file=f)

        except Exception as e:
            print(f"An error occurred: {e}", file=f)

    # --- Start the process ---
    # Initial call to the recursive helper function.
    # We start with an empty path so the root folder's name is not included.
    try:
        _list_recursively(folder_id, "")
    except Exception as e:
        print(f"An error occurred while starting the process: {e}")

    # --- Start the process ---
    # First, get the name of the root folder to start the path
    # try:
    #     root_folder = service.files().get(fileId=folder_id, fields='name').execute()
    #     root_folder_name = root_folder.get('name')
    #     print(f"Starting from root folder: {root_folder_name}")
    #
    #     # Initial call to the recursive helper function
    #     _list_recursively(folder_id, root_folder_name)
    #
    # except Exception as e:
    #     print(f"Could not find the starting folder with ID '{folder_id}'. Error: {e}")


#only for testing phase
def main():
    """Shows basic usage of the Drive v3 API."""
    creds = None
    if os.path.exists("pvt/token.json"):
        creds = Credentials.from_authorized_user_file("pvt/token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # If you changed the SCOPES, you must delete token.json for this to work.
            print("A browser window will open for you to authorize this script.")
            flow = InstalledAppFlow.from_client_secrets_file(
                "pvt/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("pvt/token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)

        # --- Example Usage of the new function ---
        print("\n--- Searching for a specific file by path ---")
        path_to_find = "nsut/about_clg/Complete Detailed Campus Map and Infrastructure Gu.pdf"
        print(f"Searching for: '{path_to_find}'")

        found_file = get_file_by_path(service, path_to_find)

        if found_file:
            print(f"\nFile Details:")
            print(f"  Name: {found_file.get('name')}")
            print(f"  ID: {found_file.get('id')}")
            print(f"  ID: {found_file.get('id')}")

            # --- Create and print the sharable link ---
            # print("\n--- Creating a sharable link ---")
            # sharable_link = create_sharable_link(service, found_file.get("id"))
            # if sharable_link:
            #     print(f"\nPublic Link: {sharable_link}")

            print("\n--- Downloading file content ---")
            file_content = download_file_content(service, found_file.get("id"))

            if file_content:
                # Check if the file is likely a PDF before trying to read it
                if found_file.get('name', '').lower().endswith('.pdf'):
                    print("\n--- Reading PDF Content ---")
                    try:
                        # Use io.BytesIO to treat the downloaded bytes as a file in memory
                        pdf_file = io.BytesIO(file_content)

                        # Create a PDF reader object
                        reader = PdfReader(pdf_file)

                        # Loop through each page and extract the text
                        full_text = ""
                        for i, page in enumerate(reader.pages):
                            text = page.extract_text()
                            if text:
                                # print(f"--- Page {i+1} ---")
                                # print(text)
                                full_text += text + "\n"

                        print("--- Full Text Extracted from PDF ---")
                        print(full_text)

                    except Exception as e:
                        print(f"Could not read the PDF file. Error: {e}")
                else:
                    # Fallback for non-PDF files (like the original code)
                    print("\nFile is not a PDF. Attempting to decode as text...")
                    try:
                        print(file_content.decode('utf-8'))
                    except UnicodeDecodeError:
                        print("File is binary and could not be displayed as text.")


        else:
            print(f"\nCould not find the file at the specified path.")
        print("-" * 40)

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()





