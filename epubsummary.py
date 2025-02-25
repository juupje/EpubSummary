import os, sys
import time
import zipfile
import logging
import xml.etree.ElementTree as ET
from ollama import chat, ChatResponse, Options
import html
import threading, queue
import tempfile
import glob

logger = logging.getLogger("BookSummary")

ns = {"epub": "http://www.idpf.org/2007/ops", "xhtml": "http://www.w3.org/1999/xhtml"}
toc_ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
def _unpack_epub(input_path:str):
    #unpack zip file
    # todo create a temp folder
    temp_folder = "temp"#tempfile.mkdtemp() 
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(temp_folder)
    return temp_folder

def _looks_like_chapter(text:str, title:str):
    title = title.lower()
    if title in ["contents", "table of contents", "toc", "index", "acknowledgements", "copyright", "about the author"]:
        return False
    if title.startswith("also by"):
        return False
    if text.count("\n") < 5:
        return False
    if text.count(" ") < 20:
        return False
    #get average line length
    lines = text.split("\n")
    if sum(len(x) for x in lines) / len(lines) < 25:
        return False
    return True
    
def _parse_chapter(file:str, title:str):
    text = ""
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
    logger.debug(f"Chapter: {title} -> {'Is a chapter' if _looks_like_chapter(text_nice, title) else 'Not a chapter'}")
    if _looks_like_chapter(text_nice, title):
        return f"Chapter: {title}\n" + text_nice
    return None
    
def _extract_text(folder:str):
    #try to find the toc.xhtml file
    pieces = []
    #we need to find the toc.ncx file
    path = os.path.join(folder, "**", "toc.ncx")
    toc_files = glob.glob(path, recursive=True)
    if len(toc_files) == 0:
        logger.error("Cannot find toc.ncx file :(")
        sys.exit(1)
    toc_file = toc_files[0]
    root_folder = os.path.dirname(toc_file)
    if toc_file is None:
        logger.error("Cannot find toc.ncx file :(")
        sys.exit(1)
    os.makedirs(os.path.join(folder, "extracted"), exist_ok=True)
    tree = ET.parse(toc_file)
    root = tree.getroot()
    #get the title
    booktitle = ET.tostring(root.find(".//ncx:docTitle", toc_ns), method="text", encoding="unicode")

    #find all navPage tags
    for elem in root.findall(".//ncx:navPoint", toc_ns):
        title = elem.find(".//ncx:text", toc_ns).text
        file = elem.find(".//ncx:content", toc_ns).attrib["src"]
        print(title, file)
        if not file.endswith(".xhtml"):
            logger.debug("Ignoring non-xhtml file: " + file)
            continue
        logger.debug(f"Processing {title} ({file})")
        text = _parse_chapter(os.path.join(root_folder, file), title)
        if text:
            pieces.append((title, text))
            with open(os.path.join(folder, "extracted", f"{os.path.splitext(title)[0]}.txt"), "w") as f:
                f.write(text)
    return booktitle, pieces

def summarize(file:str, model:str, format:str):
    folder = _unpack_epub(file)
    title, pieces = _extract_text(folder)
    def generator():
        msgs = [{
            'role': 'system',
            'content': 'You are an AI used to summarize chapters of books. '\
                        "You are given the contents of a book, one chapter at a time. Summarize each chapter, one by one. If a chapter has no content (for example, if it's just a title page), you can skip it and simply reply 'skip'. "\
                        "For each chapter, you will receive summaries of the previous chapters and the text of the current chapter. "\
                        "Your goal is to summarize the current chapter in a way that is concise and informative. "\
                        "- Do not include anything that is not part of the book, such as the table of contents. "\
                        "- Do not make up content, stick to the actual text of the book. "\
                        "- Do not add additional opinions or commentary, just summarize the content. "\
                        "- Write in full sentences, DO NOT use bullet points or lists in your replies. "
        }]
        #q = queue.Queue()
        for i, piece in enumerate(pieces):
            logger.info("Summarizing chapter: '" + piece[0] + "'")
            '''def func():
                q.put(chat(model=model, messages=msgs + [{'role': 'user', 'content': piece[1]}],
                           options=Options(num_predict=512)))
            thread = threading.Thread(target=func, daemon=True)
            thread.start()
            print("Generating summary", end="")
            while thread.is_alive():
                try:
                    response = q.get(timeout=2)
                except queue.Empty:
                    time.sleep(1)
                    print(".", end="")'''
            response = chat(model=model, messages=msgs + [{'role': 'user', 'content': piece[1] + "\n\nSummarize the above chapter. Do not use bullet points or lists in your summary. Write in full sentences."}],
                           options=Options(num_predict=512))
            #remove the think tags
            content:str = response["message"]["content"]
            start, end = content.find("<think>"), content.find("</think>")
            if start != -1 and end != -1:
                content = content[:content.find("<think>")]+content[content.find("</think>")+8:]
            if content.strip().lower() == "skip":
                continue
            yield (piece[0], content)
            msgs.append({"role": "user", "content": f"Summary of chapter {i+1}:\n{content}"})

    if format == "markdown":
        with open(f"{title}_summary.md", "w") as f:
            f.write("# Book Summary\n")
            for title, summary in generator():
                f.write(f"## {title}\n")
                f.write(summary+"\n\n-----\n")
                f.flush()
    elif format == "text":
        with open(f"{title}_summary.txt", "w") as f:
            for title, summary in generator():
                f.write(f"{title}\n")
                f.write(summary+"\n"+"-"*20+"\n")
                f.flush()
    #os.removedirs(folder)

    
if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input file path")
    parser.add_argument("--model", type=str, required=True, help="The name of the Ollama model to use")
    parser.add_argument("--debug", help="Enable debug logging", action='store_true')
    parser.add_argument("--format", help="Output format", choices=["markdown", "text"], default="text")
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

    summarize(args.input, model=args.model, format=args.format)
