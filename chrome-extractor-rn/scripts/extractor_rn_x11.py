#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
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


@dataclass
class CaptureResult:
    index: int
    url: str
    item_dir: Path
    window: ChromeWindow
    screenshot_paths: list[Path]
    interaction_error: str


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
        wm_class = parts[2].lower()
        if "chrome" not in wm_class and "chromium" not in wm_class:
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


def get_active_window_id() -> str | None:
    result = run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], check=False)
    match = re.search(r"window id # (0x[0-9a-fA-F]+)", result.stdout)
    if not match:
        return None
    return match.group(1).lower()


def choose_target_window(windows: list[ChromeWindow], hint: str | None, active_window_id: str | None, before_ids: set[str]) -> ChromeWindow:
    if hint:
        return choose_window(windows, hint)
    if active_window_id:
        for window in windows:
            if window.window_id.lower() == active_window_id:
                return window
    new_windows = [window for window in windows if window.window_id not in before_ids]
    if new_windows:
        return new_windows[-1]
    return choose_window(windows, None)


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_x11_session() -> None:
    session_type = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if session_type and session_type != "x11":
        raise SystemExit(f"unsupported session type: {session_type}")
    if not os.environ.get("DISPLAY"):
        raise SystemExit("missing DISPLAY for X11 session")


def extract_urls(raw_inputs: list[str]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw_input in raw_inputs:
        matches = re.findall(r"https?://[^\s<>'\"`]+", raw_input)
        if not matches and raw_input.startswith(("http://", "https://")):
            matches = [raw_input]
        for match in matches:
            url = match.rstrip(".,;:!?)]}>'\"，。；：！？）】")
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    if not urls:
        raise SystemExit("no URL found in input")
    return urls


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


def build_report(results: list[CaptureResult], root_dir: Path) -> str:
    lines = [
        "# Chrome Visual Extraction",
        "",
        f"- Total items: {len(results)}",
        "",
    ]
    for result in results:
        screenshot_text = ", ".join(str(path.relative_to(root_dir)) for path in result.screenshot_paths)
        lines.extend(
            [
                f"## Item {result.index}",
                "",
                f"- URL: {result.url}",
                f"- Output dir: {result.item_dir.relative_to(root_dir)}",
                f"- Window title: {result.window.title}",
                f"- Screenshots: {screenshot_text}",
                f"- Interaction error: {result.interaction_error or 'none'}",
                "",
                "### To Fill After Visual Review",
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
            ]
        )
    return "\n".join(lines)


def capture_item(
    url: str,
    item_index: int,
    root_dir: Path,
    wait_seconds: float,
    window_hint: str,
    skip_comment_scroll: bool,
    max_pages: int,
    scroll_steps: int,
) -> CaptureResult:
    item_dir = root_dir / f"item_{item_index}"
    screenshot_dir = item_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    before_ids = {window.window_id for window in list_chrome_windows()}
    open_url(url)
    time.sleep(wait_seconds)
    windows = list_chrome_windows()
    active_window_id = get_active_window_id()
    target_window = choose_target_window(windows, window_hint or None, active_window_id, before_ids)
    activate_window(target_window.window_id)
    page_1 = screenshot_dir / "page_1.png"
    save_window_screenshot(page_1)
    screenshot_paths = [page_1]
    seen_hashes = {file_sha256(page_1)}
    interaction_error = ""
    if not skip_comment_scroll:
        try:
            geometry = get_window_geometry(target_window.window_id)
            controller = XController()
            controller.press_key("Escape")
            time.sleep(0.5)
            comment_x = geometry["x"] + int(geometry["width"] * 0.87)
            comment_y = geometry["y"] + int(geometry["height"] * 0.62)
            controller.click(comment_x, comment_y)
            time.sleep(0.5)
            while len(screenshot_paths) < max_pages:
                controller.scroll_down(scroll_steps)
                time.sleep(0.8)
                next_page = screenshot_dir / f"page_{len(screenshot_paths) + 1}.png"
                save_window_screenshot(next_page)
                next_hash = file_sha256(next_page)
                if next_hash in seen_hashes:
                    next_page.unlink(missing_ok=True)
                    break
                seen_hashes.add(next_hash)
                screenshot_paths.append(next_page)
        except Exception as exc:  # noqa: BLE001
            interaction_error = str(exc)
    manifest = {
        "item_index": item_index,
        "url": url,
        "window": asdict(target_window),
        "screenshots": [str(path) for path in screenshot_paths],
        "output_dir": str(item_dir),
        "interaction_error": interaction_error,
    }
    (item_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return CaptureResult(
        index=item_index,
        url=url,
        item_dir=item_dir,
        window=target_window,
        screenshot_paths=screenshot_paths,
        interaction_error=interaction_error,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Visually capture one or more pages from local GUI Chrome.")
    parser.add_argument("inputs", nargs="+", help="One or more URLs or raw text blocks containing URLs")
    parser.add_argument("--out-dir", default="", help="Directory for screenshots and metadata")
    parser.add_argument("--wait-seconds", type=float, default=8.0, help="Wait after opening the URL")
    parser.add_argument("--window-hint", default="", help="Prefer a Chrome window whose title contains this text")
    parser.add_argument("--skip-comment-scroll", action="store_true", help="Only capture the initial page")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum screenshots to keep for one link")
    parser.add_argument("--scroll-steps", type=int, default=8, help="Mouse-wheel steps between screenshots")
    args = parser.parse_args()

    require_binary("wmctrl")
    require_binary("xwininfo")
    require_binary("gnome-screenshot")
    require_binary("xprop")
    require_x11_session()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "tmp" / f"chrome_capture_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = extract_urls(args.inputs)
    results = [
        capture_item(
            url,
            index,
            out_dir,
            args.wait_seconds,
            args.window_hint,
            args.skip_comment_scroll,
            args.max_pages,
            args.scroll_steps,
        )
        for index, url in enumerate(urls, start=1)
    ]
    (out_dir / "REPORT.md").write_text(
        build_report(results, out_dir),
        encoding="utf-8",
    )
    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
