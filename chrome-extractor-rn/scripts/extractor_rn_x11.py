#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ChromeWindow:
    window_id: str
    desktop: str
    wm_class: str
    host: str
    title: str


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def require_binary(name: str) -> None:
    if not shutil_which(name):
        raise SystemExit(f"missing required binary: {name}")


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def list_chrome_windows() -> list[ChromeWindow]:
    result = run(["wmctrl", "-lx"])
    windows: list[ChromeWindow] = []
    for raw_line in result.stdout.splitlines():
        parts = raw_line.split(None, 4)
        if len(parts) < 5:
            continue
        if parts[2] != "google-chrome.Google-chrome":
            continue
        windows.append(
            ChromeWindow(
                window_id=parts[0],
                desktop=parts[1],
                wm_class=parts[2],
                host=parts[3],
                title=parts[4],
            )
        )
    return windows


def choose_window(windows: list[ChromeWindow], hint: str | None) -> ChromeWindow:
    if not windows:
        raise SystemExit("no visible Chrome window found")
    if hint:
        lowered = hint.lower()
        for window in windows:
            if lowered in window.title.lower():
                return window
    return windows[0]


def get_window_geometry(window_id: str) -> dict[str, int]:
    result = run(["xwininfo", "-id", window_id])
    text = result.stdout

    def find_int(pattern: str) -> int:
        match = re.search(pattern, text)
        if not match:
            raise SystemExit(f"failed to parse window geometry for {pattern}")
        return int(match.group(1))

    return {
        "x": find_int(r"Absolute upper-left X:\s+(-?\d+)"),
        "y": find_int(r"Absolute upper-left Y:\s+(-?\d+)"),
        "width": find_int(r"Width:\s+(\d+)"),
        "height": find_int(r"Height:\s+(\d+)"),
    }


def activate_window(window_id: str) -> None:
    run(["wmctrl", "-ia", window_id], capture=False)
    time.sleep(1.0)


def open_url(url: str) -> None:
    chrome = shutil_which("google-chrome") or shutil_which("google-chrome-stable") or shutil_which("chromium")
    if not chrome:
        raise SystemExit("no Chrome/Chromium binary found")
    subprocess.Popen([chrome, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_window_screenshot(path: Path) -> None:
    run(["gnome-screenshot", "-w", "-f", str(path)], capture=False)


class XController:
    def __init__(self) -> None:
        from Xlib import X, XK, display  # type: ignore
        from Xlib.ext import xtest  # type: ignore

        self.X = X
        self.XK = XK
        self.display = display.Display()
        self.root = self.display.screen().root
        self.xtest = xtest

    def press_key(self, key_name: str) -> None:
        keycode = self.display.keysym_to_keycode(self.XK.string_to_keysym(key_name))
        self.xtest.fake_input(self.display, self.X.KeyPress, keycode)
        self.xtest.fake_input(self.display, self.X.KeyRelease, keycode)
        self.display.sync()

    def click(self, x: int, y: int) -> None:
        self.root.warp_pointer(x, y)
        self.display.sync()
        time.sleep(0.2)
        self.xtest.fake_input(self.display, self.X.ButtonPress, 1)
        self.xtest.fake_input(self.display, self.X.ButtonRelease, 1)
        self.display.sync()

    def scroll_down(self, steps: int) -> None:
        for _ in range(steps):
            self.xtest.fake_input(self.display, self.X.ButtonPress, 5)
            self.xtest.fake_input(self.display, self.X.ButtonRelease, 5)
            self.display.sync()
            time.sleep(0.12)


def build_report_template(url: str, window: ChromeWindow, screenshot_paths: list[Path]) -> str:
    lines = [
        "# Chrome Visual Extraction",
        "",
        f"- URL: {url}",
        f"- Window title: {window.title}",
        f"- Screenshots: {', '.join(str(path) for path in screenshot_paths)}",
        "",
        "## To Fill After Visual Review",
        "",
        "- Author:",
        "- Note title:",
        "- Publish time / location:",
        "- Media type:",
        "- Visible text:",
        "- Visible comments:",
        "- Engagement data:",
        "- Notes:",
        "",
        "## Markdown Output",
        "",
        "Replace this section with the final Markdown summary after reviewing the screenshots.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Visually capture a page from local GUI Chrome.")
    parser.add_argument("url", help="Page URL to capture from Chrome")
    parser.add_argument("--out-dir", default="", help="Directory for screenshots and metadata")
    parser.add_argument("--wait-seconds", type=float, default=8.0, help="Wait after opening the URL")
    parser.add_argument("--window-hint", default="", help="Prefer a Chrome window whose title contains this text")
    parser.add_argument("--skip-comment-scroll", action="store_true", help="Only capture the initial page")
    args = parser.parse_args()

    require_binary("wmctrl")
    require_binary("xwininfo")
    require_binary("gnome-screenshot")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "tmp" / f"chrome_extractor_rn_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    before_ids = {window.window_id for window in list_chrome_windows()}
    open_url(args.url)
    time.sleep(args.wait_seconds)

    windows = list_chrome_windows()
    target_window = None
    new_windows = [window for window in windows if window.window_id not in before_ids]
    if args.window_hint:
        target_window = choose_window(windows, args.window_hint)
    elif new_windows:
        target_window = new_windows[-1]
    else:
        target_window = choose_window(windows, None)

    activate_window(target_window.window_id)

    page_1 = out_dir / "page_1.png"
    save_window_screenshot(page_1)
    screenshot_paths = [page_1]

    interaction_error = ""
    if not args.skip_comment_scroll:
        try:
            geometry = get_window_geometry(target_window.window_id)
            controller = XController()
            controller.press_key("Escape")
            time.sleep(0.5)
            comment_x = geometry["x"] + int(geometry["width"] * 0.87)
            comment_y = geometry["y"] + int(geometry["height"] * 0.62)
            controller.click(comment_x, comment_y)
            time.sleep(0.5)
            controller.scroll_down(8)
            time.sleep(0.8)
            page_2 = out_dir / "page_2.png"
            save_window_screenshot(page_2)
            screenshot_paths.append(page_2)
        except Exception as exc:  # noqa: BLE001
            interaction_error = str(exc)

    manifest = {
        "url": args.url,
        "timestamp": timestamp,
        "window": asdict(target_window),
        "screenshots": [str(path) for path in screenshot_paths],
        "output_dir": str(out_dir),
        "interaction_error": interaction_error,
        "command_hint": f"python3 {shlex.quote(str(Path(__file__)))} {shlex.quote(args.url)}",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "REPORT_TEMPLATE.md").write_text(
        build_report_template(args.url, target_window, screenshot_paths),
        encoding="utf-8",
    )

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
