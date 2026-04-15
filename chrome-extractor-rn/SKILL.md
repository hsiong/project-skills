---
name: chrome-extractor-rn
description: Use when the user sends `extract-rn <link>` or `extract-rn <multi links>`. It handles one or more links that need one Chrome-based visual extraction report, triggers for phrases like `extract-rn https://...` or `extract-rn 3 links`, and should not trigger for curl, scraping, headless-browser tasks, or non-link coding work.
---

# Chrome Visual Extractor

Use this skill for tasks like:

- "extract-rn https://example.com/post/123"
- "extract-rn 这3个链接都抓一下"

## Rules

- Only use the local GUI Chrome session.
- Reuse the user's existing Chrome window if one is already running.
- Do not use `curl`, requests-based scraping, Chrome DevTools protocol scraping, or headless Chromes.
- Prefer visual capture plus model-side image reading.
- Keep the workflow additive. Do not modify the user's existing project files unless explicitly requested.

## Quick Workflow

1. Confirm the user gave one or more links, usually with the wake word `extract-rn`.
2. Detect the current system and session type before choosing a script.
3. Run the matching bundled capture script with one or more URLs or raw text blocks that contain URLs.
4. Open the generated screenshots with `view_image`.
5. Read visible title, 正文, 评论, 互动数据, 媒体类型 from the screenshots.
6. Write the final Markdown summary.

## Script

Choose the script by system instead of hardcoding one path first.

1. Detect the OS and session:

```bash
uname -s
cat /etc/os-release
printf '%s\n' "${XDG_SESSION_TYPE:-}"
```

2. If the system is Linux Mint 22, run:

```bash
python3 chrome-extractor-rn/scripts/extractor_rn_x11.py '<url1>' '<url2>'
```

or:

```bash
python3 chrome-extractor-rn/scripts/extractor_rn_x11.py '62 ... https://example.com/a' '88 ... https://example.com/b'
```

3. If the system is not Linux Mint 22:

- First verify the session is X11.
- Then look under `chrome-extractor-rn/scripts/` for a script that matches the current OS and session.
- If no matching script exists yet, stop and tell the user this system is not supported by the skill yet.

Optional arguments:

- `--out-dir <dir>`: custom output directory
- `--wait-seconds <n>`: extra wait after opening URL
- `--window-hint <text>`: prefer a Chrome window whose title contains this text
- `--skip-comment-scroll`: only capture the initial screen
- `--max-pages <n>`: maximum screenshots to keep for one link
- `--scroll-steps <n>`: mouse-wheel steps between screenshots

## Output

The script writes:

- `item_n/screenshots/page_1.png`: the first screenshot for one link
- `item_n/screenshots/page_2.png` ... `item_n/screenshots/page_n.png`: additional screenshots while scrolling until no new visual content is detected
- `item_n/manifest.json`: per-link metadata and file list
- `REPORT.md`: merged Markdown scaffold for all links

## Notes

- The current bundled script targets Linux Mint 22 with X11, `wmctrl`, `gnome-screenshot`, and GUI Chrome.
- The script requires an X11 session. If Python Xlib is unavailable, the initial capture still works but comment scrolling is skipped.
- Scrolling stops when a new screenshot matches a previously captured image for the same link, or when `--max-pages` is reached.
