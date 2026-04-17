---
name: extractor-rn-vision
description: Use when the user sends `extractor-rn-vision <link>` or `extractor-rn-vision <multi links>`. Do not trigger for curl, scraping, headless-browser tasks, or ordinary coding work.
---

# Chrome Visual Extractor

Use this skill for tasks like:

- "extractor-rn-vision https://example.com/post/123"
- "extractor-rn-vision 这3个链接都抓一下"

## Rules

- Only use the local GUI Chrome session.
- Reuse the user's existing Chrome window if one is already running.
- Do not use `curl`, requests-based scraping, Chrome DevTools protocol scraping, or headless Chromes.
- Prefer visual capture plus model-side image reading.
- Keep the workflow additive. Do not modify the user's existing project files unless explicitly requested.
- If `extractor-rn-vision-main` does not exist yet, first create that Xephyr session and end the current turn immediately.
- After creating a missing `extractor-rn-vision-main` session, do not rerun the capture command in the same turn and do not poll in the background.

## Quick Workflow

1. Confirm the user gave one or more links, usually with the wake word `extractor-rn-vision`.
2. Detect the current system and session type before choosing a script.
3. For Linux Mint 22 X11, treat `extractor-rn-vision-main` as the default persistent Xephyr session.
4. If that session is missing, start it once, tell the user to log in inside the Xephyr window if needed, and stop there for this turn.
5. If that session already exists, run the matching bundled capture script with one or more URLs or raw text blocks that contain URLs.
6. On each visible comments page, click every visible `展开 n 条回复` action before saving the screenshot.
7. Re-scan the current page after each click because reply expansion changes the page layout.
8. Open the generated screenshots with `view_image`.
9. Read visible title, 正文, 评论, 互动数据, 媒体类型 from the screenshots.
10. Write the final Markdown summary.

## Final Summary Rules

- `title`、`正文`、`评论`、`互动数据`、`媒体类型` must stay as raw visible data. Do not rewrite them into polished prose.
- Analyze images from the screenshots with `view_image`.
- For video posts, analyze the cover image only. Do not infer unseen video content.
- In `互动数据`, expand each visible conversation thread to include 2 replies when available.
- Treat `展开 n 条回复` as a page action. Click each visible one on the current page, then re-check the page because the comment layout may shift.
- Split `互动数据` by conversation block with fenced code blocks, for example:

```text
- xxx
- xx
```

```text
- xxx
- xx
```

- If the page is unavailable and the generated `REPORT.md` already marks it as unavailable, keep the final Markdown summary to that result instead of fabricating missing fields.

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
python3 extractor-rn-vision/scripts/extractor_html_x11.py '<url1>' '<url2>'
```

or:

```bash
python3 extractor-rn-vision/scripts/extractor_html_x11.py '62 ... https://example.com/a' '88 ... https://example.com/b'
```

Linux Mint 22 X11 session handling:

- The default session name is `extractor-rn-vision-main`.
- If the session does not exist, let the script create it and stop after that command finishes.
- Do not issue a second capture command in the same turn after the session is first created.
- Do not keep waiting, polling, or background-looping for login completion.
- Only on a later user command, or when the session already exists before this turn starts, continue to the actual capture run.

3. If the system is not Linux Mint 22:

- First verify the session is X11.
- Then look under `extractor-rn-vision/scripts/` for a script that matches the current OS and session.
- If no matching script exists yet, stop and tell the user this system is not supported by the skill yet.

Optional arguments:

- `--out-dir <dir>`: custom output directory, default is None
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
- The default Linux Mint flow runs inside the persistent `extractor-rn-vision-main` Xephyr session, so capture input does not take over the user's main desktop pointer.
