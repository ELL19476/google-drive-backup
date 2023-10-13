import os
import argparse
from sanitize_filename import sanitize
import create_service
import data_parser
from colors import color

# To connect to googel drive api
# If modifying these scopes, delete the file token.pickle
CLIENT_SECRET_FILE = "client_secret.json"
API_NAME = "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly", 
          "https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/drive.activity.readonly",
          "https://www.googleapis.com/auth/documents.readonly"]

SUPPORTED_MIMETYPES: list = ["application/vnd.google-apps.document"]

# prefix, text, link
DATA = []
docs_service = None

def get_uname(item):
    return sanitize(item["name"])

# Find mimetype of file & parse it if it is a document
def exportFile(item):
    if SUPPORTED_MIMETYPES[0] == str(item["mimeType"]):
            # parse document
            global DATA
            global docs_service
            if not docs_service:
                docs_service = data_parser.create_docs_service()
            # print(f"{color.PURPLE}{color.BOLD}Parsing document: {get_uname(item)}{color.END}\n{color.ITALIC}This may take a few seconds...{color.END}")
            DATA.extend(data_parser.parse_doc(item["id"], docs_service))
            # print("Done!\n")

# Search for files in a specific drive
def listfiles(driveID = None, fileIDs = None):
    page_token = None
    fileList = []
    while True:
        query = "("
        mimeQuery = ""
        for mimeType in SUPPORTED_MIMETYPES:
            if mimeQuery:
                mimeQuery += " or "
            mimeQuery += "mimeType = '" + mimeType + "'"
        mimeQuery += ") "
        query += mimeQuery
        
        if fileIDs:
            query += "and ("
            fileQuery = ""
            for fileID in fileIDs:
                if fileQuery:
                    fileQuery += " or "
                fileQuery += "'" + fileID + "' in parents"
            fileQuery += ") "
            query += fileQuery

        if driveID:
            results = (
                service.files()
                .list(
                    pageSize=1000,
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    driveId=driveID,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="drive"
                )
                .execute()
            )
        else:
            results = (
                service.files()
                .list(
                    pageSize=1000,
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="domain"
                )
                .execute()
            )
        fileList.extend(results.get("files", []))
        page_token = results.get("nextPageToken", None)
        if page_token is None:     
            break
    return fileList


# return all drives the user has access to
def get_drive_list(maxDrives = 100): 
    return service.drives().list(pageSize=maxDrives).execute()["drives"]

def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--id",
        type=str,
        nargs="+",
        help="Specific files or folders ID you would like to download.",
    )
    parser.add_argument(
        "-d",
        "--drive",
        type=str,
        nargs="+",
        help="Specific drive IDs you would like to download.",
    )
    opt = parser.parse_args()
    return opt
    
def main(opt):
    global DATA
    if not opt.id and not opt.drive:
        print(f"{color.RED}Alert: Folder or Files ID to download must be provided.{color.END}")
        return
    if opt.id:
        files = listfiles(drive)
        for file in files:
            exportFile(file)
    if opt.drive:
        for drive in opt.drive:
            files = listfiles(drive)
            for file in files:
                exportFile(file)
        
    return DATA

def instantiate_service():
    global service
    service = create_service.Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)    
    return service

if __name__ == "__main__":
    instantiate_service()
    opt = parse_opt()
    main(opt)