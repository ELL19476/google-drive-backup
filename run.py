import os
from colors import color

def main():
    print("INSTALLING REQUIREMENTS... \n")
    os.system("pip install -r requirements.txt")
    import download
    download.instantiate_service()
    drives = download.get_drive_list()
    print('*' * 50)
    print(f"Found {color.GREEN}{drives.__len__()}{color.END} possible drives to backup...")

    import webform
    settings = webform.main(driveList=drives)
    # exclude drives
    if "exclude-drives" in settings:
        drives = [drive for drive in drives if drive["id"] not in settings["exclude-drives"]]
    
    options: Options = Options()
    options.output = settings["backup-folder"]
    options.drive = [drive["id"] for drive in drives]

    download.main(options)

class Options:
    output = ""
    link = None
    name = None
    id = None
    drive = None
        

if __name__ == "__main__":
    main()
