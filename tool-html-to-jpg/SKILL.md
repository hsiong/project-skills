---
name: tool-html-to-jpg
description: Convert local HTML pages to high-quality JPG screenshots when users say "convert this HTML to JPG," "render this webpage as JPEG," or "export the article as an image." Do not trigger for HTML editing, remote website capture, or general image manipulation.
---

# HTML to JPG

Use the bundled `scripts/html_to_jpg.py` to render a local HTML file with Chrome, Chromium, or Edge and save it as a JPG.

## Workflow

1. Resolve the input HTML path and optional output path. Use absolute paths in commands.
2. When executing or testing, use project dependencies; never use global pip to pollute global dependencies. If no project environment exists, create and use a temporary environment at `/tmp/tool-html-to-jpg/bin/python`, and remove the temporary environment after execution finishes.
3. Ensure a supported browser is installed. If automatic discovery fails, ask the user for its executable path and set `CHROME_PATH` for the command.
4. Run:

   ```bash
   python3 \
     scripts/html_to_jpg.py \
     /absolute/path/input.html \
     /absolute/path/output.jpg \
     750 \
     95
   ```

   The output path, width, and JPEG quality are optional. By default, the image is written beside the HTML file with the same stem, at 750 pixels wide and quality 95.
5. Report the generated image path. If rendering fails, preserve the source HTML and explain whether the missing browser, timeout, or invalid path caused the failure.

The renderer reads local resources through the input file URL, estimates a full-page viewport, removes trailing blank space, and flattens transparency onto white before JPEG encoding.
