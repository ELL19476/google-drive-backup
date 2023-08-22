import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import io
import argparse
from tqdm import tqdm
from googleapiclient.http import MediaIoBaseDownload
import re
from sanitize_filename import sanitize

# To connect to googel drive api
# If modifying these scopes, delete the file token.pickle
CLIENT_SECRET_FILE = "client_secret.json"
API_NAME = "drive"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly", 
          "https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/drive.activity.readonly"]

# Create a Google Drive API service
def Create_Service(client_secret_file, api_name, api_version, *scopes):
    print(client_secret_file, api_name, api_version, scopes, sep="-")
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f"token_{API_SERVICE_NAME}_{API_VERSION}.pickle"

    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, "wb") as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME.capitalize(), "service created successfully.\n")
        return service
    except Exception as e:
        print("Unable to connect.")
        print(e)
        return None

def get_uname(item):
    # get file extension
    ext = item["name"].split(".")[-1]
    os.rename(item["name"], f"{item['name']}.{ext}")
    return sanitize(item["name"])
def downloadFiles(item, des):
    match str(item["mimeType"]):
        case str("application/vnd.google-apps.folder"):
            if not os.path.isdir(des):
                os.mkdir(path=des)
            listfolders(item["id"], des)
        case str("application/vnd.google-apps.document"):
            downloadMediaFiles(item["id"], des + ".docx", mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        case str("application/vnd.google-apps.spreadsheet"):
            downloadMediaFiles(item["id"], des + ".xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        case str("application/vnd.google-apps.presentation"):
            downloadMediaFiles(item["id"], des + ".pptx", mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        case str("application/vnd.google-apps.drawing"):
            downloadMediaFiles(item["id"], des + ".jpg", mimetype="image/jpeg")
        case str("application/vnd.google-apps.script"):
            downloadMediaFiles(item["id"], des + ".json", mimetype="application/vnd.google-apps.script+json")
        case str("application/vnd.google-apps.form"):
            downloadMediaFiles(item["id"], des + ".pdf", mimetype="application/pdf")
        case str("application/vnd.google-apps.map"):
            downloadMediaFiles(item["id"], des + ".json", mimetype="application/vnd.google-apps.map+json")
        case str("application/vnd.google-apps.site"):
            downloadMediaFiles(item["id"], des + ".json", mimetype="application/vnd.google-apps.site+json")
        case _:
            downloadMediaFiles(item["id"], des)

def downloadMediaFiles(dowid, dfilespath, folder=None, mimetype=None):
    if mimetype:
        request = service.files().export_media(fileId=dowid, mimeType=mimetype)
    else:
        request = service.files().get_media(fileId=dowid)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    pbar = tqdm(total=100, ncols=70)
    while done is False:
        status, done = downloader.next_chunk()
        if status:
            pbar.update(int(status.progress() * 100) - pbar.n)
    pbar.close()
    if folder:
        with io.open(folder + "/" + dfilespath, "wb") as f:
            fh.seek(0)
            f.write(fh.read())
    else:
        with io.open(dfilespath, "wb") as f:
            fh.seek(0)
            f.write(fh.read())


# List files in folder until all files are found
def listfolders(filid, des):
    page_token = None
    while True:
        results = (
            service.files()
            .list(
                pageSize=1000,
                q="'" + filid + "'" + " in parents",
                fields="nextPageToken, files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            )
            .execute()
        )
        folder = results.get("files", [])
        for item in folder:
            filePath = os.path.join(des, get_uname(item))
            downloadFiles(item, filePath)

        page_token = results.get("nextPageToken", None)
        if page_token is None:     
            break
    return folder


# Download folders with files
def downloadfolders(folder_ids):
    print("Downloading folders...")
    for folder_id in folder_ids:
        print("Downloading folder: " + get_uname(service.files().get(fileId=folder_id).execute()))
    for folder_id in folder_ids:
        folder = service.files().get(fileId=folder_id).execute()
        folder_name = get_uname(folder)
        page_token = None
        while True:
            results = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents",
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                )
                .execute()
            )

            items = results.get("files", [])
            #send all items in this section
            if not items:
                # download files
                downloadFiles(folder, os.path.join(os.getcwd(), folder_name))
            else:
                # download folders
                print(f"Start downloading folder '{folder_name}'.")
                for item in items:
                    if item["mimeType"] == "application/vnd.google-apps.folder":
                        if not os.path.isdir(folder_name):
                            os.mkdir(folder_name)
                        bfolderpath = os.path.join(os.getcwd(), folder_name)
                        if not os.path.isdir(
                            os.path.join(bfolderpath, get_uname(item))
                        ):
                            os.mkdir(os.path.join(bfolderpath, get_uname(item)))

                        folderpath = os.path.join(bfolderpath, get_uname(item))
                        listfolders(item["id"], folderpath)
                    else:
                        if not os.path.isdir(folder_name):
                            os.mkdir(folder_name)
                        bfolderpath = os.path.join(os.getcwd(), folder_name)

                        filepath = os.path.join(bfolderpath, get_uname(item))
                        downloadFiles(item, filepath)
                        print(get_uname(item))
            
            page_token = results.get("nextPageToken", None)
            if page_token is None:
                break

# Search id of specific folder name under a parent folder id
def get_gdrive_id(folder_ids, folder_names):
    for folder_id in folder_ids:
        for folder_name in folder_names:
            print(folder_name)
            page_token = None
            while True:
                response = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'and name = '{folder_name}'",
                        spaces="drive",
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    )
                    .execute()
                )
                for file in response.get("files", []):
                    print("Found file: %s (%s)\n" % (get_uname(file), file.get("id")))
                
                downloadfolders([file.get("id")])

                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--id",
        type=str,
        nargs="+",
        help="Specific files or folders ID you would like to download (Must have).",
    )
    parser.add_argument(
        "-d",
        "--drive",
        type=str,
        nargs="+",
        help="Specific drive IDs you would like to download (Optional).",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        nargs="*",
        help="Specific folder names you would like to download (Optional).",
    )
    parser.add_argument(
        "-l",
        "--link",
        type=str,
        nargs="+",
        help="Specific links you would like to download (Must have).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        nargs="?",
        default="",
        help="Specific output folder you would like to download (Optional).",
    )
    opt = parser.parse_args()
    return opt

def extract_drive_id(links):
    # Remove any leading or trailing spaces from the link
    print(links)
    output = []
    for link in links:
        link = link.strip()

        if "folders" in link:
            pattern = r"(?<=folders\/)[^/|^?]+"
        else:
            pattern = r"(?<=/d/|id=)[^/|^?]+"

        match = re.search(pattern, link)
    
        if match:
            output.append(match.group())
    if output:
        return output
    else:
        return None
    
def main(opt):
    if opt.output != "":
        if not os.path.isdir(opt.output):
            os.mkdir(opt.output)
            print("Output folder created.")
        os.chdir(opt.output)
    if opt.link:
        uniq_id = extract_drive_id(opt.link)
        downloadfolders(uniq_id)
    elif opt.name:
        uniq_id = extract_drive_id(opt.link)
        get_gdrive_id(uniq_id, opt.name)
    elif opt.id:
        downloadfolders(opt.id)
    elif opt.drive:
        downloadDrives(opt.drive)
    else:
        print("Alert: Folder or Files ID to download must be provided.")

def instantiate_service():
    global service
    service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)    

def get_drive_list(maxDrives = 100): 
    return service.drives().list(pageSize=maxDrives).execute()["drives"]

def downloadDrives(driveIds):
    output_path = os.getcwd()
    for driveID in driveIds:  
        os.chdir(output_path)
        drive = service.drives().get(driveId=driveID).execute()
        des = os.path.join(output_path, get_uname(drive))
        if not os.path.isdir(des):
            os.mkdir(des)
        os.chdir(des)
        while True:
            results = service.files().list(
                driveId=driveID,
                spaces="drive",                 
                fields="nextPageToken, files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive"
            ).execute()
            

            items = results.get("files", [])
            #send all items in this section
            if not items:
                # download files
                downloadFiles(drive, des)
            else:
                # download folders
                print(f"Start downloading drive '{get_uname(drive)}'.")
                for item in items:
                    if item["mimeType"] == "application/vnd.google-apps.folder":
                        if not os.path.isdir( os.path.join(des, get_uname(item))):
                            os.mkdir(os.path.join(des, get_uname(item)))

                        folderpath = os.path.join(des, get_uname(item))
                        listfolders(item["id"], folderpath)
                    else:
                        filepath = os.path.join(des, get_uname(item))
                        downloadFiles(item, filepath)
                        print(get_uname(item))
            
            page_token = results.get("nextPageToken", None)
            if page_token is None:
                break


if __name__ == "__main__":
    instantiate_service()
    opt = parse_opt()
    main(opt)
