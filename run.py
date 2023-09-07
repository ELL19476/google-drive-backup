import os, sys
from colors import color

# Disable
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore
def enablePrint():
    sys.stdout = sys.__stdout__

def main():
    print("INSTALLING REQUIREMENTS... \n")
    os.system("pip install -r requirements.txt")
    print(f"\n{color.GREEN}All dependencies installed.{color.END}\n")
    
    import collector
    collector.instantiate_service()
    drives = collector.get_drive_list()
    print('*' * 50)
    print(f"Found {color.GREEN}{drives.__len__()}{color.END} possible drives to download...")

    import webform
    settings = webform.main(driveList=drives)
    # exclude drives
    if "exclude-drives" in settings:
        drives = [drive for drive in drives if drive["id"] not in settings["exclude-drives"]]
    
    options: Options = Options()
    print()
    print('*' * 50)
    print("Downloading following drives:")
    for drive in drives:
        print(f"{color.GREEN}{drive['name']}{color.END}")
    options.drive = [drive["id"] for drive in drives]
    print()

    print('*' * 50)
    sections = collector.main(options)
    print('*' * 50)
    print("\n\n")

    print(f"{color.GREEN}{color.BOLD}Finished constructing document tree.{color.END}")

    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = [sec["text"] for sec in sections]
    
    metadata = [{"title": sec["headers"][0] if len(sec["headers"]) > 0 else "", "section": ": ".join(sec["headers"][1:]), "source": sec["link"]} for sec in sections]
    documents = text_splitter.create_documents(texts, metadata)
    # write to file
    print('*' * 50)
    print(f"{color.GREEN}{color.BOLD}Success.{color.END}\nReturning document tree.")
    return text_splitter.split_documents(documents)

class Options:
    link = None
    name = None
    id = None
    drive = None
        

if __name__ == "__main__":
    main()
