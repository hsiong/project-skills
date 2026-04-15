---
name: chrome-extractor-rn
description: Use when the user sends `extract-rn <link>`. It handles visible text, images, comments, and media details by operating the local GUI Chrome session, triggers for phrases like `extract https://...` or `用 Chrome 可视化提取这个链接`, and should not trigger for curl/scraping/headless-browser tasks or non-link coding work.
---

# Chrome Visual Extractor

Use this skill for tasks like:

- "extract-rn https://example.com/post/123"

## Rules

- Only use the local GUI Chrome session.
- Reuse the user's existing Chrome window if one is already running.
- Do not use `curl`, requests-based scraping, Chrome DevTools protocol scraping, or headless Chromes.
- Prefer visual capture plus model-side image reading.
- Keep the workflow additive. Do not modify the user's existing project files unless explicitly requested.

## Quick Workflow

1. Confirm the user gave a link, usually with the wake word `extract`.
2. Detect the current system and session type before choosing a script.
3. Run the matching bundled capture script with the Chrome URL.
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
python3 chrome-extractor-rn/scripts/extractor_rn_x11.py '<url>'
```

3. If the system is not Linux Mint 22:

- First verify the session is X11.
- Then look under `chrome-visual-extractor/scripts/` for a script that matches the current OS and session.
- If no matching script exists yet, stop and tell the user this system is not supported by the skill yet.

Optional arguments:

- `--out-dir <dir>`: custom output directory
- `--wait-seconds <n>`: extra wait after opening URL
- `--window-hint <text>`: prefer a Chrome window whose title contains this text
- `--skip-comment-scroll`: only capture the initial screen

## Output

The script writes:

- `page_1.png`: initial visible page
- `page_2.png`: comment area after a visual scroll attempt
- `manifest.json`: metadata and file list
- `REPORT_TEMPLATE.md`: Markdown scaffold for the final write-up

## Notes

- The current bundled script targets Linux Mint 22 with X11, `wmctrl`, `gnome-screenshot`, and GUI Chrome.
- The script uses Python Xlib for key and mouse events. If Xlib is unavailable, capture still works but scrolling is skipped.
