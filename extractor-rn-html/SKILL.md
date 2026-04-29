---
name: extractor-rn-html
description: Use only when the user sends `extractor-rn-html <link>`. This skill handles the X11/Xephyr GUI Chrome flow that opens Xiaohongshu links, expands comments and replies, exports expanded HTML, parses content with an Ollama-compatible model, recognizes downloaded images, and generates `manifest.json`, `RESULT.md`, and `ANALYSIS.md`. Do not trigger for screenshot-only parsing, curl/headless scraping, or ordinary coding work.
---

# Chrome HTML Extractor (X11)

Use this skill for tasks like:

- "extractor-rn-html https://example.com/post/123"

## Rules

- `extractor-rn-html` is an independent skill. Do not treat it as depending on `chrome-extractor-rn`.
- Keep the current X11/Xephyr framework. Do not rewrite the flow into screenshots, curl scraping, CDP scraping, or a headless browser pipeline.
- Keep the local GUI Chrome workflow and preserve the existing comment expansion logic, including visible `展开 n 条回复` actions and comment-panel scrolling.
- The main extractor is `scripts/extractor_html_x11.py`.
- `scripts/cdp_x11.py` is only a helper for Chrome remote-debugging setup and clicking visible `展开 n 条回复` targets from the GUI flow. Do not use it to replace the extractor with CDP scraping.
- The image recognizer is `scripts/extractor_image.py`.
- The final report analyzer is `scripts/analyse.py`.
- After comments and replies are expanded as far as the page allows, export the current page HTML and use that HTML as the primary analysis input.
- `scripts/extractor_html_x11.py` should export HTML, split and clean it for model analysis, extract `title`、`正文`、`评论`、`互动数据`、`图片`、`视频`, download note images, and write `manifest.json` plus `RESULT.md`.
- After `scripts/extractor_html_x11.py` finishes successfully, run `scripts/extractor_image.py` on the same output directory. It writes `图片识别` back into each `manifest.json` and rebuilds `RESULT.md`.
- After image recognition succeeds, run `scripts/analyse.py` on the same output directory to read `RESULT.md` and write `ANALYSIS.md`.
- If no reusable session exists, `scripts/extractor_html_x11.py` should start a new Xephyr session, open Chrome for manual login, then stop. At that point the assistant must end the current flow immediately, tell the user to log in manually, and tell the user that they need to send a new `extractor-rn-html <link>` request after login. Do not continue in the background, and do not treat it as the current session's rerun.
- All model scripts must use an Ollama-compatible chat endpoint; allow model name, base URL, API path, and timeout overrides from user arguments.
- Default to `gemma4:26b` for HTML parsing in `extractor_html_x11.py`, `qwen3-vl:8b` for image recognition in `extractor_image.py`, and `qwen3.6:27b` for final report analysis in `analyse.py`, unless the user specifies other compatible values.
- Treat image and video extraction as model-side analysis from the expanded HTML and downloaded media, not screenshot OCR.
- For videos, only recognize the visible cover, poster, or current frame that is actually available to the model input. Do not infer unseen content.
- `title`、`正文`、`评论`、`互动数据` must stay close to the source content. Do not rewrite them into polished prose.
- `互动数据` should be formatted as `点赞: xx, 收藏: xx, 评论: xx, 分享：xx`.
- Emojis in text and comments should be output as `![emoji](emoji_url)` if possible (often found with `class="xxx-emoji"` tags).
- `评论` should be formatted as markdown blocks for each parent-comment, for example:

```markdown
- x:msg
    - ...可能多条
    - 可能 xx(作者):msg
    - ...可能多条
```

## Quick Workflow

1. Confirm the user input is `extractor-rn-html <link>`.
2. Run `scripts/extractor_html_x11.py`.
3. If the script reports no reusable session and opens a fresh login session, stop there, tell the user to finish login manually, and end the current model flow. The next extraction must come from a new user message `extractor-rn-html <link>`, not from a background rerun in the current session.
4. If a reusable session exists, let the extractor open the link, expand visible comments and replies, export the expanded page HTML, and write parsed fields plus downloaded images into each `item_n/manifest.json`.
5. Immediately run `scripts/extractor_image.py` on that same output directory and write `图片识别` into each manifest.
6. Run `scripts/analyse.py` on that same output directory and write `ANALYSIS.md`.
7. Return the final output directory containing refreshed manifests, `RESULT.md`, and `ANALYSIS.md`.

## Execution Notes

- Prefer the bundled implementation under `extractor-rn-html/`.
- When the user supplies a model or endpoint override, pass it through to the bundled implementation instead of hardcoding defaults in the prompt.
- The current Linux X11 flow starts with:

```bash
python3 extractor-rn-html/scripts/extractor_html_x11.py '<url1>' '<url2>'
```

- After extraction succeeds, run image analysis on the same output directory:

```bash
python3 extractor-rn-html/scripts/extractor_image.py --out-dir <extractor_output_dir>
```

- After image analysis succeeds, run final report analysis on the same output directory:

```bash
python3 extractor-rn-html/scripts/analyse.py --out-dir <extractor_output_dir>
```

- Common overrides:
  `--ollama-base-url <url>`
  `--ollama-api-path <path>`
  `--ollama-model <model>`
  `--ollama-timeout <seconds>`
  `--xephyr-session <session_name>`
  `--image-limit <n>`
  `--video-limit <n>`
  `--wait-seconds <seconds>`
  `--skip-comment-scroll`
  `--chunk-size <n>`
  `--max-predict <n>`

## Output

- `item_n/expanded_page.html`: expanded HTML exported from the current Chrome page.
- `item_n/expanded_page_analyse.html`: cleaned HTML chunk source written before model analysis.
- `item_n/images/`: downloaded note images referenced by the parsed result.
- `item_n/manifest.json`: capture metadata plus parsed `title`、`正文`、`评论`、`互动数据`、`图片`、`视频`; after `extractor_image.py`, it also contains `图片识别`.
- `RESULT.md`: merged report generated from the parsed manifests.
- `ANALYSIS.md`: final strategy analysis generated from `RESULT.md`.
