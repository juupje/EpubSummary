# EpubSummary
Summarize eBooks using AI

## Requirements
You should have [ollama](https://github.com/ollama/ollama) installed and have pulled an LLM. Depending on which model you use (such as DeepSeek, Qwen of LLaMa), the quality of the summary will be better or worse.

## Usage
1. Obtain an ebook (in `.epub` format). If you have an `.ascm` file, you can use a tool such as [knock](https://github.com/esn/knock) to get the corresponding `.epub` file.
2. Run `python3 epubsummary.py [epub_file] --model [model_name]`. Note that this can take quite a long time, depending on which model you're using and the length of the book.
3. Enjoy your AI generated summary of the book!