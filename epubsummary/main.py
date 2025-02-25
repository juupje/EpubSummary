import argparse
import os
import sys
import zipfile
import logging
import xml.etree.ElementTree as ET
logger = logging.getLogger("BookSummary")

ns = {"epub": "http://www.idpf.org/2007/ops", "xhtml": "http://www.w3.org/1999/xhtml"}
def unpack_epub(input_path:str):
    #unpack zip file
    # todo create a temp folder
    temp_folder = "temp"    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(temp_folder)
    #check if OEPBS folder exists
    if not os.path.exists(os.path.join(temp_folder, "OEBPS")):
        logger.error("OEBPS folder not found")
        sys.exit(1)
    
    #try to find the toc.xhtml file
    if os.path.isfile(toc_file := os.path.join(temp_folder, "OEBPS", "toc.xhtml")):
        os.makedirs(os.path.join(temp_folder, "extracted"), exist_ok=True)
        tree = ET.parse(toc_file)
        root = tree.getroot()
        #find all a tags
        for elem in root.findall(".//xhtml:a", ns):
            file = elem.attrib["href"]
            title = elem.text
            logger.debug(f"Processing {title} ({file})")
            text = parse_chapter(os.path.join(temp_folder, "OEBPS", file), elem.text)
            with open(os.path.join(temp_folder, "extracted", f"{os.path.splitext(title)[0]}.txt"), "w") as f:
                f.write(text)
                
def parse_chapter(file:str, title:str):
    text = f"Chapter: {title}\n"
    with open(file, "r") as f:
        root = ET.parse(f).getroot()
        #find all p tags
        for elem in root.findall(".//xhtml:p", ns):
            #read the content of the p tag, without all the html tags
            text += ET.tostring(elem, method="text", encoding="unicode")
            if not text.endswith("\n"):
                text += "\n"
    text_nice = ""
    for line in text.split("\n"):
        x = line.strip()
        if len(x)>0:
            text_nice += x + "\n"
    return text_nice
    

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, required=True, help="Input file path")
    parser.add_argument("--debug", help="Enable debug logging", action='store_true')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        sys.exit(1)
    ext = os.path.splitext(args.input)[1]
    if ext != ".epub":
        print(f"Input file must be an epub file: {args.input}")
        sys.exit(1)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    unpack_epub(args.input)
