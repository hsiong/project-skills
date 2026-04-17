#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from http import HTTPStatus
from pathlib import Path
from urllib import error, request

import numpy as np


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
    window: ChromeWindow | None
    screenshot_paths: list[Path]
    interaction_error: str
    skipped_capture: bool
    result_summary: str
    precheck_status_code: int | None
    precheck_location: str
    stop_reason: str


@dataclass
class PrecheckResult:
    skipped_capture: bool
    status_code: int | None
    location: str
    result_summary: str


@dataclass
class XephyrSessionState:
    name: str
    display: str
    screen: str
    profile_dir: str
    xephyr_pid: int
    metacity_pid: int
    created_at: str


@dataclass
class ExpandReplyTarget:
    x: int
    y: int
    min_y: int
    max_y: int
    min_x: int
    max_x: int
    width: int
    height: int
    is_occluded: bool
    occlusion_reason: str


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
    result = run(["wmctrl", "-lx"], check=False)
    if result.returncode != 0:
        return []
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


def get_window_by_id(window_id: str) -> ChromeWindow | None:
    lowered_id = window_id.lower()
    for window in list_chrome_windows():
        if window.window_id.lower() == lowered_id:
            return window
    return None


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


def spawn_background_process(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    stdout=None,
    stderr=None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        command,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=stdout if stdout is not None else subprocess.DEVNULL,
        stderr=stderr if stderr is not None else subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def spawn_detached_user_service(command: list[str], *, env: dict[str, str] | None = None) -> bool:
    systemd_run = shutil_which("systemd-run")
    if not systemd_run:
        return False
    unit_suffix = hashlib.sha1("\0".join(command).encode("utf-8")).hexdigest()[:10]
    unit_name = f"extractor-rn-vision-chrome-{int(time.time() * 1000)}-{unit_suffix}"
    run_command = [
        systemd_run,
        "--user",
        "--quiet",
        "--collect",
        "--service-type=exec",
        "--unit",
        unit_name,
    ]
    if env is not None:
        base_env = os.environ
        for key, value in env.items():
            if base_env.get(key) != value:
                run_command.extend(["--setenv", f"{key}={value}"])
        for key in base_env:
            if key not in env:
                run_command.extend(["--setenv", f"{key}="])
    run_command.extend(command)
    result = subprocess.run(
        run_command,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        close_fds=True,
    )
    return result.returncode == 0


def open_url(
    url: str,
    *,
    new_window: bool = False,
    profile_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    chrome = shutil_which("google-chrome") or shutil_which("google-chrome-stable") or shutil_which("chromium")
    if not chrome:
        raise SystemExit("no Chrome/Chromium binary found")
    command = [chrome]
    if new_window:
        command.append("--new-window")
    if profile_dir is not None:
        profile_dir.mkdir(parents=True, exist_ok=True)
        command.extend(
            [
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
    command.append(url)
    if new_window and spawn_detached_user_service(command, env=env):
        return
    spawn_background_process(command, env=env)


def key_event(controller: XController, key_name: str, is_press: bool) -> None:
    if controller.backend == "python-xlib":
        keysym = controller.XK.string_to_keysym(key_name)
        keycode = controller.display.keysym_to_keycode(keysym)
        event_type = controller.X.KeyPress if is_press else controller.X.KeyRelease
        controller.xtest.fake_input(controller.display, event_type, keycode)
        controller.display.sync()
        return
    keysym = controller.lib_x11.XStringToKeysym(key_name.encode("utf-8"))
    keycode = controller.lib_x11.XKeysymToKeycode(controller.display, keysym)
    controller.lib_xtst.XTestFakeKeyEvent(controller.display, keycode, 1 if is_press else 0, 0)
    controller.lib_x11.XSync(controller.display, 0)


def tap_key(controller: XController, key_name: str) -> None:
    key_event(controller, key_name, True)
    time.sleep(0.03)
    key_event(controller, key_name, False)


def key_combo(controller: XController, modifiers: list[str], key_name: str) -> None:
    for modifier in modifiers:
        key_event(controller, modifier, True)
        time.sleep(0.02)
    tap_key(controller, key_name)
    time.sleep(0.02)
    for modifier in reversed(modifiers):
        key_event(controller, modifier, False)


def char_key(char: str) -> tuple[str, bool]:
    if "a" <= char <= "z":
        return char, False
    if "A" <= char <= "Z":
        return char.lower(), True
    if "0" <= char <= "9":
        return char, False
    mapping = {
        " ": ("space", False),
        ":": ("semicolon", True),
        ";": ("semicolon", False),
        "/": ("slash", False),
        "?": ("slash", True),
        ".": ("period", False),
        ">": ("period", True),
        ",": ("comma", False),
        "<": ("comma", True),
        "-": ("minus", False),
        "_": ("minus", True),
        "=": ("equal", False),
        "+": ("equal", True),
        "'": ("apostrophe", False),
        '"': ("apostrophe", True),
        "`": ("grave", False),
        "~": ("grave", True),
        "[": ("bracketleft", False),
        "{": ("bracketleft", True),
        "]": ("bracketright", False),
        "}": ("bracketright", True),
        "\\": ("backslash", False),
        "|": ("backslash", True),
        "!": ("1", True),
        "@": ("2", True),
        "#": ("3", True),
        "$": ("4", True),
        "%": ("5", True),
        "^": ("6", True),
        "&": ("7", True),
        "*": ("8", True),
        "(": ("9", True),
        ")": ("0", True),
        "\n": ("Return", False),
    }
    if char not in mapping:
        raise RuntimeError(f"unsupported character for X11 typing: {char!r}")
    return mapping[char]


def type_text(controller: XController, text: str, delay_seconds: float = 0.025) -> None:
    for char in text:
        key_name, use_shift = char_key(char)
        if use_shift:
            key_event(controller, "Shift_L", True)
        tap_key(controller, key_name)
        if use_shift:
            key_event(controller, "Shift_L", False)
        time.sleep(delay_seconds)


def open_url_in_existing_window(window_id: str, url: str) -> None:
    activate_window(window_id)
    time.sleep(0.35)
    controller = XController()
    key_combo(controller, ["Control_L"], "t")
    time.sleep(0.25)
    key_combo(controller, ["Control_L"], "l")
    time.sleep(0.12)
    type_text(controller, url)
    time.sleep(0.08)
    tap_key(controller, "Return")


def save_window_screenshot(window_id: str, path: Path) -> None:
    xwd_path = path.with_suffix(".xwd")
    try:
        run(["xwd", "-silent", "-id", window_id, "-out", str(xwd_path)], capture=False)
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "xwd_pipe",
                "-i",
                str(xwd_path),
                "-frames:v",
                "1",
                str(path),
            ],
            capture=False,
        )
    finally:
        xwd_path.unlink(missing_ok=True)


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


class NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def precheck_url(url: str, timeout: float = 10.0) -> PrecheckResult:
    opener = request.build_opener(NoRedirectHandler)
    req = request.Request(
        url,
        method="HEAD",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        },
    )
    status_code: int | None = None
    location = ""
    try:
        with opener.open(req, timeout=timeout) as response:
            status_code = response.getcode()
            location = response.headers.get("Location", "")
    except error.HTTPError as exc:
        status_code = exc.code
        location = exc.headers.get("Location", "")
    except error.URLError:
        return PrecheckResult(
            skipped_capture=False,
            status_code=None,
            location="",
            result_summary="",
        )
    except Exception:
        return PrecheckResult(
            skipped_capture=False,
            status_code=None,
            location="",
            result_summary="",
        )
    if status_code == HTTPStatus.FOUND:
        return PrecheckResult(
            skipped_capture=True,
            status_code=status_code,
            location=location,
            result_summary="页面不存在或已下架",
        )
    if status_code == HTTPStatus.NOT_FOUND and ("/404" in url or "/404" in location):
        return PrecheckResult(
            skipped_capture=True,
            status_code=status_code,
            location=location,
            result_summary="页面不存在或已下架",
        )
    return PrecheckResult(
        skipped_capture=False,
        status_code=status_code,
        location=location,
        result_summary="",
    )


def load_rgb_image(path: Path) -> np.ndarray:
    probe = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(path),
        ]
    )
    width_text, height_text = probe.stdout.strip().split("x")
    width = int(width_text)
    height = int(height_text)
    frame = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=True,
        capture_output=True,
    )
    rgb = np.frombuffer(frame.stdout, dtype=np.uint8)
    return rgb.reshape((height, width, 3))


def sample_region(
    image: np.ndarray,
    *,
    x_start_ratio: float,
    x_end_ratio: float,
    y_start_ratio: float,
    y_end_ratio: float,
    sample_height: int = 72,
    sample_width: int = 72,
) -> np.ndarray:
    height, width, _ = image.shape
    x0 = max(0, min(width - 1, int(width * x_start_ratio)))
    x1 = max(x0 + 1, min(width, int(width * x_end_ratio)))
    y0 = max(0, min(height - 1, int(height * y_start_ratio)))
    y1 = max(y0 + 1, min(height, int(height * y_end_ratio)))
    cropped = image[y0:y1, x0:x1]
    y_indices = np.linspace(0, cropped.shape[0] - 1, num=min(sample_height, cropped.shape[0]), dtype=int)
    x_indices = np.linspace(0, cropped.shape[1] - 1, num=min(sample_width, cropped.shape[1]), dtype=int)
    sampled = cropped[np.ix_(y_indices, x_indices)]
    grayscale = (
        sampled[:, :, 0].astype(np.float32) * 0.299
        + sampled[:, :, 1].astype(np.float32) * 0.587
        + sampled[:, :, 2].astype(np.float32) * 0.114
    )
    return (grayscale // 8).astype(np.uint8)


def sample_digest(sample: np.ndarray) -> str:
    return hashlib.sha256(sample.tobytes()).hexdigest()


def sample_distance(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape:
        raise ValueError("sample shapes do not match")
    delta = np.abs(left.astype(np.int16) - right.astype(np.int16))
    return float(delta.mean())


def dilate_mask(mask: np.ndarray, radius_y: int, radius_x: int) -> np.ndarray:
    height, width = mask.shape
    dilated = np.zeros_like(mask, dtype=bool)
    for dy in range(-radius_y, radius_y + 1):
        src_y0 = max(0, -dy)
        src_y1 = min(height, height - dy)
        dst_y0 = max(0, dy)
        dst_y1 = min(height, height + dy)
        for dx in range(-radius_x, radius_x + 1):
            src_x0 = max(0, -dx)
            src_x1 = min(width, width - dx)
            dst_x0 = max(0, dx)
            dst_x1 = min(width, width + dx)
            dilated[dst_y0:dst_y1, dst_x0:dst_x1] |= mask[src_y0:src_y1, src_x0:src_x1]
    return dilated


def connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, int, int, int]] = []
    points = np.argwhere(mask)
    for start_y, start_x in points:
        if visited[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        visited[start_y, start_x] = True
        min_y = max_y = int(start_y)
        min_x = max_x = int(start_x)
        while stack:
            y, x = stack.pop()
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            for next_y in range(max(0, y - 1), min(height, y + 2)):
                for next_x in range(max(0, x - 1), min(width, x + 2)):
                    if not mask[next_y, next_x] or visited[next_y, next_x]:
                        continue
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))
        components.append((min_y, max_y, min_x, max_x))
    return components


def find_expand_reply_targets(path: Path) -> list[ExpandReplyTarget]:
    image = load_rgb_image(path)
    height, width, _ = image.shape
    x0 = int(width * 0.62)
    x1 = int(width * 0.97)
    y0 = int(height * 0.16)
    y1 = int(height * 0.96)
    cropped = image[y0:y1, x0:x1]
    red = cropped[:, :, 0].astype(np.int16)
    green = cropped[:, :, 1].astype(np.int16)
    blue = cropped[:, :, 2].astype(np.int16)
    blue_mask = (
        (blue >= 85)
        & (blue - red >= 18)
        & (blue - green >= 6)
        & (green <= 190)
    )
    dilated = dilate_mask(blue_mask, radius_y=1, radius_x=6)
    candidates: list[tuple[int, int, int, int]] = []
    crop_height, crop_width = blue_mask.shape
    for min_y, max_y, min_x, max_x in connected_components(dilated):
        box_width = max_x - min_x + 1
        box_height = max_y - min_y + 1
        pixel_count = int(blue_mask[min_y:max_y + 1, min_x:max_x + 1].sum())
        center_x = min_x + box_width // 2
        aspect_ratio = box_width / max(box_height, 1)
        if box_width < 56 or box_width > 260:
            continue
        if box_height < 8 or box_height > 36:
            continue
        if aspect_ratio < 3.2:
            continue
        if pixel_count < 18 or pixel_count > 1200:
            continue
        if center_x > int(crop_width * 0.72):
            continue
        if min_y < int(crop_height * 0.05):
            continue
        candidates.append((min_y, max_y, min_x, max_x))
    merged: list[tuple[int, int, int, int]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], item[2])):
        if not merged:
            merged.append(candidate)
            continue
        prev_min_y, prev_max_y, prev_min_x, prev_max_x = merged[-1]
        min_y, max_y, min_x, max_x = candidate
        if abs(min_y - prev_min_y) <= 8 and abs(min_x - prev_min_x) <= 18:
            merged[-1] = (
                min(prev_min_y, min_y),
                max(prev_max_y, max_y),
                min(prev_min_x, min_x),
                max(prev_max_x, max_x),
            )
            continue
        merged.append(candidate)
    targets: list[ExpandReplyTarget] = []
    top_guard = max(14, int(crop_height * 0.03))
    bottom_guard = max(18, int(crop_height * 0.04))
    for min_y, max_y, min_x, max_x in merged:
        occlusion_reason = ""
        if min_y <= top_guard:
            occlusion_reason = "top"
        elif max_y >= crop_height - bottom_guard:
            occlusion_reason = "bottom"
        targets.append(
            ExpandReplyTarget(
                x=x0 + (min_x + max_x) // 2,
                y=y0 + (min_y + max_y) // 2,
                min_y=y0 + min_y,
                max_y=y0 + max_y,
                min_x=x0 + min_x,
                max_x=x0 + max_x,
                width=max_x - min_x + 1,
                height=max_y - min_y + 1,
                is_occluded=bool(occlusion_reason),
                occlusion_reason=occlusion_reason,
            )
        )
    return targets


class XController:
    def __init__(self) -> None:
        try:
            from Xlib import X, XK, display  # type: ignore
            from Xlib.ext import xtest  # type: ignore

            self.backend = "python-xlib"
            self.X = X
            self.XK = XK
            self.display = display.Display()
            self.root = self.display.screen().root
            self.xtest = xtest
        except ModuleNotFoundError:
            self.backend = "ctypes"
            self._init_ctypes()

    def _init_ctypes(self) -> None:
        self.lib_x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.lib_xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")
        self.lib_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.lib_x11.XOpenDisplay.restype = ctypes.c_void_p
        self.lib_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.lib_x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.lib_x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.lib_x11.XStringToKeysym.restype = ctypes.c_ulong
        self.lib_x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.lib_x11.XKeysymToKeycode.restype = ctypes.c_uint
        self.lib_x11.XWarpPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.lib_x11.XWarpPointer.restype = ctypes.c_int
        self.lib_x11.XFlush.argtypes = [ctypes.c_void_p]
        self.lib_x11.XFlush.restype = ctypes.c_int
        self.lib_x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib_x11.XSync.restype = ctypes.c_int
        self.lib_xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        self.lib_xtst.XTestFakeKeyEvent.restype = ctypes.c_int
        self.lib_xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        self.lib_xtst.XTestFakeButtonEvent.restype = ctypes.c_int
        self.display = self.lib_x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("failed to open X11 display")
        self.root = self.lib_x11.XDefaultRootWindow(self.display)

    def press_key(self, key_name: str) -> None:
        if self.backend == "python-xlib":
            keycode = self.display.keysym_to_keycode(self.XK.string_to_keysym(key_name))
            self.xtest.fake_input(self.display, self.X.KeyPress, keycode)
            self.xtest.fake_input(self.display, self.X.KeyRelease, keycode)
            self.display.sync()
            return
        keysym = self.lib_x11.XStringToKeysym(key_name.encode("utf-8"))
        keycode = self.lib_x11.XKeysymToKeycode(self.display, keysym)
        self.lib_xtst.XTestFakeKeyEvent(self.display, keycode, 1, 0)
        self.lib_xtst.XTestFakeKeyEvent(self.display, keycode, 0, 0)
        self.lib_x11.XSync(self.display, 0)

    def move_pointer(self, x: int, y: int) -> None:
        if self.backend == "python-xlib":
            self.root.warp_pointer(x, y)
            self.display.sync()
            return
        self.lib_x11.XWarpPointer(self.display, 0, self.root, 0, 0, 0, 0, x, y)
        self.lib_x11.XFlush(self.display)
        self.lib_x11.XSync(self.display, 0)

    def click(self, x: int, y: int) -> None:
        self.move_pointer(x, y)
        if self.backend == "python-xlib":
            time.sleep(0.2)
            self.xtest.fake_input(self.display, self.X.ButtonPress, 1)
            self.xtest.fake_input(self.display, self.X.ButtonRelease, 1)
            self.display.sync()
            return
        time.sleep(0.2)
        self.lib_xtst.XTestFakeButtonEvent(self.display, 1, 1, 0)
        self.lib_xtst.XTestFakeButtonEvent(self.display, 1, 0, 0)
        self.lib_x11.XSync(self.display, 0)

    def scroll_down(self, steps: int, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            self.move_pointer(x, y)
        if self.backend == "python-xlib":
            for _ in range(steps):
                self.xtest.fake_input(self.display, self.X.ButtonPress, 5)
                self.xtest.fake_input(self.display, self.X.ButtonRelease, 5)
                self.display.sync()
                time.sleep(0.12)
            return
        for _ in range(steps):
            self.lib_xtst.XTestFakeButtonEvent(self.display, 5, 1, 0)
            self.lib_xtst.XTestFakeButtonEvent(self.display, 5, 0, 0)
            self.lib_x11.XSync(self.display, 0)
            time.sleep(0.12)

    def scroll_up(self, steps: int, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            self.move_pointer(x, y)
        if self.backend == "python-xlib":
            for _ in range(steps):
                self.xtest.fake_input(self.display, self.X.ButtonPress, 4)
                self.xtest.fake_input(self.display, self.X.ButtonRelease, 4)
                self.display.sync()
                time.sleep(0.12)
            return
        for _ in range(steps):
            self.lib_xtst.XTestFakeButtonEvent(self.display, 4, 1, 0)
            self.lib_xtst.XTestFakeButtonEvent(self.display, 4, 0, 0)
            self.lib_x11.XSync(self.display, 0)
            time.sleep(0.12)


def comment_panel_point(geometry: dict[str, int], y_ratio: float = 0.72) -> tuple[int, int]:
    return (
        geometry["x"] + int(geometry["width"] * 0.87),
        geometry["y"] + int(geometry["height"] * y_ratio),
    )


def expand_visible_reply_links(
    window_id: str,
    geometry: dict[str, int],
    controller: XController,
    screenshot_dir: Path,
    screenshot_index: int,
) -> int:
    probe_path = screenshot_dir / f"_expand_probe_{screenshot_index}.png"
    click_targets: list[tuple[int, int]] = []
    skipped_targets: list[tuple[int, int]] = []
    retried_targets: list[tuple[str, int]] = []
    attempts = 0
    scan_rounds = 0
    while attempts < 8 and scan_rounds < 24:
        scan_rounds += 1
        save_window_screenshot(window_id, probe_path)
        targets = find_expand_reply_targets(probe_path)
        next_target: ExpandReplyTarget | None = None
        for target in targets:
            if any(abs(target.x - clicked_x) <= 14 and abs(target.y - clicked_y) <= 10 for clicked_x, clicked_y in click_targets):
                continue
            if any(abs(target.x - skipped_x) <= 20 and abs(target.y - skipped_y) <= 18 for skipped_x, skipped_y in skipped_targets):
                continue
            if target.width < 68 and target.height > 14:
                skipped_targets.append((target.x, target.y))
                continue
            next_target = target
            break
        if next_target is None:
            break
        if next_target.is_occluded:
            retry_key = (next_target.occlusion_reason, next_target.y // 48)
            scroll_x, scroll_y = comment_panel_point(geometry, y_ratio=0.72)
            if retry_key in retried_targets:
                skipped_targets.append((next_target.x, next_target.y))
                continue
            retried_targets.append(retry_key)
            if next_target.occlusion_reason == "top":
                controller.scroll_up(3, x=scroll_x, y=scroll_y)
            else:
                controller.scroll_down(3, x=scroll_x, y=scroll_y)
            time.sleep(0.7)
            continue
        controller.click(geometry["x"] + next_target.x, geometry["y"] + next_target.y)
        click_targets.append((next_target.x, next_target.y))
        attempts += 1
        time.sleep(0.9)
    probe_path.unlink(missing_ok=True)
    return len(click_targets)


COMMENT_PANEL_REGION = {
    "x_start_ratio": 0.63,
    "x_end_ratio": 0.98,
    "y_start_ratio": 0.24,
    "y_end_ratio": 0.96,
}

HEADER_REGION = {
    "x_start_ratio": 0.63,
    "x_end_ratio": 0.98,
    "y_start_ratio": 0.05,
    "y_end_ratio": 0.22,
}

MAIN_IMAGE_REGION = {
    "x_start_ratio": 0.05,
    "x_end_ratio": 0.58,
    "y_start_ratio": 0.12,
    "y_end_ratio": 0.90,
}


def is_main_image_dominant(image: np.ndarray) -> bool:
    left_sample = sample_region(image, **MAIN_IMAGE_REGION, sample_height=84, sample_width=84)
    comment_sample = sample_region(image, **COMMENT_PANEL_REGION, sample_height=84, sample_width=84)
    left_variance = float(np.var(left_sample.astype(np.float32)))
    comment_variance = float(np.var(comment_sample.astype(np.float32)))
    return left_variance >= 12.0 and left_variance >= comment_variance * 2.2


def wait_for_x_display(display_name: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run(["xdpyinfo", "-display", display_name], check=False)
        if result.returncode == 0:
            return
        time.sleep(0.2)
    raise SystemExit(f"failed to start display {display_name}")


def sanitize_session_name(raw_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw_name.strip())
    cleaned = cleaned.strip("-._")
    if not cleaned:
        raise SystemExit("xephyr session name is empty after sanitization")
    return cleaned


def session_root_dir() -> Path:
    return Path.cwd() / "tmp" / "xephyr_sessions"


def session_dir_for(name: str) -> Path:
    return session_root_dir() / sanitize_session_name(name)


def session_state_path(session_dir: Path) -> Path:
    return session_dir / "session.json"


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def load_session_state(session_name: str) -> XephyrSessionState | None:
    state_path = session_state_path(session_dir_for(session_name))
    if not state_path.exists():
        return None
    data = json.loads(state_path.read_text(encoding="utf-8"))
    state = XephyrSessionState(**data)
    if not (pid_is_alive(state.xephyr_pid) and pid_is_alive(state.metacity_pid)):
        state_path.unlink(missing_ok=True)
        return None
    return state


def write_session_state(session_name: str, state: XephyrSessionState) -> None:
    session_dir = session_dir_for(session_name)
    session_dir.mkdir(parents=True, exist_ok=True)
    session_state_path(session_dir).write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def session_display_env(display_name: str) -> dict[str, str]:
    env = os.environ.copy()
    env["DISPLAY"] = display_name
    env["XDG_SESSION_TYPE"] = "x11"
    env.pop("WAYLAND_DISPLAY", None)
    return env


def default_profile_dir_for_session(session_name: str) -> Path:
    return session_dir_for(session_name) / "chrome-profile"


def start_xephyr_session(session_name: str, display_name: str, screen: str, profile_dir: Path) -> XephyrSessionState:
    require_binary("Xephyr")
    require_binary("metacity")
    require_binary("xdpyinfo")
    display_env = session_display_env(display_name)
    session_dir = session_dir_for(session_name)
    session_dir.mkdir(parents=True, exist_ok=True)
    xephyr_log = (session_dir / "xephyr.log").open("ab")
    metacity_log = (session_dir / "metacity.log").open("ab")
    xephyr = subprocess.Popen(
        [
            "Xephyr",
            display_name,
            "-screen",
            screen,
            "-ac",
            "-br",
        ],
        stdin=subprocess.DEVNULL,
        stdout=xephyr_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    try:
        wait_for_x_display(display_name)
        metacity = spawn_background_process(
            [
                "metacity",
                "--display",
                display_name,
                "--sm-disable",
            ],
            env=display_env,
            stdout=metacity_log,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        xephyr.terminate()
        try:
            xephyr.wait(timeout=5)
        except subprocess.TimeoutExpired:
            xephyr.kill()
        raise
    state = XephyrSessionState(
        name=sanitize_session_name(session_name),
        display=display_name,
        screen=screen,
        profile_dir=str(profile_dir),
        xephyr_pid=xephyr.pid,
        metacity_pid=metacity.pid,
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    write_session_state(session_name, state)
    return state


def effective_xephyr_session_name(args: argparse.Namespace) -> str:
    return sanitize_session_name(args.xephyr_session or "extractor-rn-vision-main")


def ensure_xephyr_session(args: argparse.Namespace) -> tuple[XephyrSessionState, bool]:
    session_name = effective_xephyr_session_name(args)
    state = load_session_state(session_name)
    if state is not None:
        return state, False
    profile_dir = Path(args.chrome_profile_dir) if args.chrome_profile_dir else default_profile_dir_for_session(session_name)
    return start_xephyr_session(session_name, args.xephyr_display, args.xephyr_screen, profile_dir), True


def close_xephyr_session(session_name: str) -> int:
    state = load_session_state(session_name)
    if state is None:
        print(f"xephyr session not found: {sanitize_session_name(session_name)}")
        return 0
    for pid in [state.metacity_pid, state.xephyr_pid]:
        try:
            os.kill(pid, 15)
        except OSError:
            continue
    session_state_path(session_dir_for(session_name)).unlink(missing_ok=True)
    print(f"closed xephyr session: {sanitize_session_name(session_name)}")
    return 0


def wait_for_target_window(before_ids: set[str], wait_seconds: float, hint: str | None) -> ChromeWindow:
    deadline = time.time() + max(wait_seconds, 10.0)
    while time.time() < deadline:
        windows = list_chrome_windows()
        active_window_id = get_active_window_id()
        if windows:
            try:
                return choose_target_window(windows, hint or None, active_window_id, before_ids)
            except SystemExit:
                pass
        time.sleep(0.5)
    raise SystemExit("timed out waiting for Chrome window")


def ensure_login_window(session_state: XephyrSessionState, url: str) -> None:
    display_env = session_display_env(session_state.display)
    windows_before = list_chrome_windows()
    if windows_before:
        existing_window = choose_target_window(windows_before, None, get_active_window_id(), set())
        open_url_in_existing_window(existing_window.window_id, url)
    else:
        open_url(
            url,
            new_window=True,
            profile_dir=Path(session_state.profile_dir),
            env=display_env,
        )
    time.sleep(2.0)
    if not list_chrome_windows():
        raise SystemExit("failed to open Chrome inside Xephyr session")


def maybe_rerun_in_xephyr(args: argparse.Namespace) -> int | None:
    wants_xephyr = bool(args.inputs) or args.prepare_login or bool(args.close_xephyr_session) or args.xephyr or bool(args.xephyr_session)
    if not wants_xephyr:
        return None
    if args.close_xephyr_session:
        return close_xephyr_session(args.close_xephyr_session)
    session_state, created = ensure_xephyr_session(args)
    current_display = os.environ.get("DISPLAY", "")
    if created:
        original_display = os.environ.get("DISPLAY")
        os.environ.update(session_display_env(session_state.display))
        try:
            ensure_login_window(session_state, args.login_url or "https://www.xiaohongshu.com")
        finally:
            if original_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = original_display
        print(f"xephyr session started: {session_state.name}")
        print(f"display={session_state.display}")
        print(f"profile_dir={session_state.profile_dir}")
        print("login in the Xephyr window, then rerun the same command")
        return 0
    if args.prepare_login:
        original_display = os.environ.get("DISPLAY")
        os.environ.update(session_display_env(session_state.display))
        try:
            ensure_login_window(session_state, args.login_url or "https://www.xiaohongshu.com")
        finally:
            if original_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = original_display
        print(f"xephyr session ready: {session_state.name}")
        print(f"display={session_state.display}")
        print(f"profile_dir={session_state.profile_dir}")
        return 0
    if current_display == session_state.display:
        return None
    rerun_args = [value for value in sys.argv[1:] if value != "--xephyr"]
    if "--prepare-login" in rerun_args:
        rerun_args.remove("--prepare-login")
    rerun = subprocess.run(
        [sys.executable, __file__, *rerun_args],
        env=session_display_env(session_state.display),
        check=False,
    )
    return rerun.returncode


def build_report(results: list[CaptureResult], root_dir: Path) -> str:
    lines = [
        "# Chrome Visual Extraction",
        "",
        f"- Total items: {len(results)}",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"## Item {result.index}",
                "",
                f"- URL: {result.url}",
            ]
        )
        if result.result_summary:
            lines.append(f"- Result: {result.result_summary}")
        if result.precheck_status_code is not None:
            lines.append(f"- HTTP precheck: {result.precheck_status_code}")
        if result.precheck_location:
            lines.append(f"- Redirect location: {result.precheck_location}")
        if result.skipped_capture:
            lines.append("")
            continue
        if result.stop_reason:
            lines.append(f"- Stop reason: {result.stop_reason}")
        screenshot_text = ", ".join(str(path.relative_to(root_dir)) for path in result.screenshot_paths)
        lines.extend(
            [
                f"- Output dir: {result.item_dir.relative_to(root_dir)}",
                f"- Window title: {result.window.title if result.window else 'none'}",
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
    chrome_profile_dir: Path | None,
) -> CaptureResult:
    item_dir = root_dir / f"item_{item_index}"
    item_dir.mkdir(parents=True, exist_ok=True)
    precheck = precheck_url(url)
    if precheck.skipped_capture:
        manifest = {
            "item_index": item_index,
            "url": url,
            "window": None,
            "screenshots": [],
            "output_dir": str(item_dir),
            "interaction_error": "",
            "skipped_capture": True,
            "result_summary": precheck.result_summary,
            "precheck_status_code": precheck.status_code,
            "precheck_location": precheck.location,
            "stop_reason": "",
        }
        (item_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return CaptureResult(
            index=item_index,
            url=url,
            item_dir=item_dir,
            window=None,
            screenshot_paths=[],
            interaction_error="",
            skipped_capture=True,
            result_summary=precheck.result_summary,
            precheck_status_code=precheck.status_code,
            precheck_location=precheck.location,
            stop_reason="",
        )
    screenshot_dir = item_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    before_windows = list_chrome_windows()
    before_ids = {window.window_id for window in before_windows}
    active_window_id = get_active_window_id()
    existing_window: ChromeWindow | None = None
    if before_windows:
        existing_window = choose_target_window(before_windows, window_hint or None, active_window_id, set())
        activate_window(existing_window.window_id)
        time.sleep(0.6)
    if existing_window is not None:
        open_url_in_existing_window(existing_window.window_id, url)
    else:
        open_url(url, new_window=True, profile_dir=chrome_profile_dir)
    time.sleep(wait_seconds)
    if existing_window is not None:
        refreshed_window = get_window_by_id(existing_window.window_id)
        target_window = refreshed_window or existing_window
    else:
        target_window = wait_for_target_window(before_ids, wait_seconds, window_hint or None)
    activate_window(target_window.window_id)
    screenshot_paths: list[Path] = []
    seen_hashes: set[str] = set()
    seen_comment_digests: set[str] = set()
    interaction_error = ""
    stop_reason = ""
    try:
        geometry = get_window_geometry(target_window.window_id)
        controller = XController()
        controller.press_key("Escape")
        time.sleep(0.5)
        baseline_header_sample: np.ndarray | None = None
        previous_comment_sample: np.ndarray | None = None
        initial_title = target_window.title
        stagnant_rounds = 0
        tail_probe_rounds = 0
        while len(screenshot_paths) < max_pages:
            expanded_count = expand_visible_reply_links(
                target_window.window_id,
                geometry,
                controller,
                screenshot_dir,
                len(screenshot_paths) + 1,
            )
            scroll_x, scroll_y = comment_panel_point(geometry)
            next_page = screenshot_dir / f"page_{len(screenshot_paths) + 1}.png"
            save_window_screenshot(target_window.window_id, next_page)
            current_window = get_window_by_id(target_window.window_id)
            if current_window is not None and initial_title and current_window.title != initial_title:
                stop_reason = f"window title changed from '{initial_title}' to '{current_window.title}'"
                next_page.unlink(missing_ok=True)
                break
            image = load_rgb_image(next_page)
            header_sample = sample_region(image, **HEADER_REGION)
            if baseline_header_sample is None:
                baseline_header_sample = header_sample
            elif sample_distance(header_sample, baseline_header_sample) >= 4.5:
                stop_reason = "page header changed, likely switched to a different note"
                next_page.unlink(missing_ok=True)
                break
            comment_sample = sample_region(image, **COMMENT_PANEL_REGION)
            if is_main_image_dominant(image):
                stop_reason = "page focus moved to main image area"
                next_page.unlink(missing_ok=True)
                break
            comment_digest = sample_digest(comment_sample)
            if comment_digest in seen_comment_digests:
                if expanded_count == 0 and tail_probe_rounds < 3:
                    tail_probe_rounds += 1
                    next_page.unlink(missing_ok=True)
                    controller.scroll_down(max(1, scroll_steps // 2), x=scroll_x, y=scroll_y)
                    time.sleep(0.8)
                    continue
                stop_reason = "comment panel repeated"
                next_page.unlink(missing_ok=True)
                break
            if previous_comment_sample is not None:
                comment_distance = sample_distance(comment_sample, previous_comment_sample)
                if comment_distance <= 0.35:
                    stagnant_rounds += 1
                else:
                    stagnant_rounds = 0
            if stagnant_rounds >= 3 and expanded_count == 0:
                if tail_probe_rounds < 3:
                    tail_probe_rounds += 1
                    next_page.unlink(missing_ok=True)
                    controller.scroll_down(max(1, scroll_steps // 2), x=scroll_x, y=scroll_y)
                    time.sleep(0.8)
                    continue
                stop_reason = "comment panel stopped changing"
                next_page.unlink(missing_ok=True)
                break
            next_hash = file_sha256(next_page)
            if next_hash in seen_hashes:
                if expanded_count == 0 and tail_probe_rounds < 3:
                    tail_probe_rounds += 1
                    next_page.unlink(missing_ok=True)
                    controller.scroll_down(max(1, scroll_steps // 2), x=scroll_x, y=scroll_y)
                    time.sleep(0.8)
                    continue
                stop_reason = "window screenshot repeated"
                next_page.unlink(missing_ok=True)
                break
            seen_hashes.add(next_hash)
            seen_comment_digests.add(comment_digest)
            previous_comment_sample = comment_sample
            tail_probe_rounds = 0
            screenshot_paths.append(next_page)
            if skip_comment_scroll:
                stop_reason = "skip_comment_scroll enabled"
                break
            controller.scroll_down(scroll_steps, x=scroll_x, y=scroll_y)
            time.sleep(1.2)
        if not stop_reason and len(screenshot_paths) >= max_pages:
            stop_reason = f"reached max_pages={max_pages}"
    except Exception as exc:  # noqa: BLE001
        interaction_error = str(exc)
        if not screenshot_paths:
            fallback_path = screenshot_dir / "page_1.png"
            save_window_screenshot(target_window.window_id, fallback_path)
            screenshot_paths.append(fallback_path)
    manifest = {
        "item_index": item_index,
        "url": url,
        "window": asdict(target_window),
        "screenshots": [str(path) for path in screenshot_paths],
        "output_dir": str(item_dir),
        "interaction_error": interaction_error,
        "skipped_capture": False,
        "result_summary": "",
        "precheck_status_code": precheck.status_code,
        "precheck_location": precheck.location,
        "stop_reason": stop_reason,
    }
    (item_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return CaptureResult(
        index=item_index,
        url=url,
        item_dir=item_dir,
        window=target_window,
        screenshot_paths=screenshot_paths,
        interaction_error=interaction_error,
        skipped_capture=False,
        result_summary="",
        precheck_status_code=precheck.status_code,
        precheck_location=precheck.location,
        stop_reason=stop_reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Visually capture one or more pages from local GUI Chrome.")
    parser.add_argument("inputs", nargs="*", help="One or more URLs or raw text blocks containing URLs")
    parser.add_argument("--out-dir", default="", help="Directory for screenshots and metadata")
    parser.add_argument("--wait-seconds", type=float, default=8.0, help="Wait after opening the URL")
    parser.add_argument("--window-hint", default="", help="Prefer a Chrome window whose title contains this text")
    parser.add_argument("--skip-comment-scroll", action="store_true", help="Only capture the initial page")
    parser.add_argument("--max-pages", type=int, default=40, help="Maximum screenshots to keep for one link")
    parser.add_argument("--scroll-steps", type=int, default=10, help="Mouse-wheel steps between screenshots")
    parser.add_argument("--chrome-profile-dir", default="", help="Use a dedicated Chrome profile directory")
    parser.add_argument("--xephyr", action="store_true", help="Deprecated compatibility flag; capture now prefers the persistent extractor-rn-vision-main Xephyr session by default")
    parser.add_argument("--xephyr-session", default="", help="Persistent Xephyr session name to reuse login state, defaulting to extractor-rn-vision-main")
    parser.add_argument("--xephyr-display", default=":99", help="Nested Xephyr display name")
    parser.add_argument("--xephyr-screen", default="1400x2200", help="Nested Xephyr screen size")
    parser.add_argument("--prepare-login", action="store_true", help="Start or reuse a Xephyr session and open Chrome for manual login")
    parser.add_argument("--login-url", default="", help="Optional URL to open while preparing login")
    parser.add_argument("--close-xephyr-session", default="", help="Close a persistent Xephyr session by name")
    args = parser.parse_args()

    rerun_code = maybe_rerun_in_xephyr(args)
    if rerun_code is not None:
        return rerun_code

    require_binary("wmctrl")
    require_binary("xwininfo")
    require_binary("xwd")
    require_binary("xprop")
    require_binary("ffmpeg")
    require_binary("ffprobe")
    require_x11_session()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "tmp" / f"chrome_capture_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.prepare_login or args.close_xephyr_session:
        return 0
    if not args.inputs:
        raise SystemExit("no URL found in input")
    wants_xephyr = bool(args.inputs) or args.prepare_login or args.xephyr or bool(args.xephyr_session)
    if wants_xephyr and not args.chrome_profile_dir:
        chrome_profile_dir = default_profile_dir_for_session(effective_xephyr_session_name(args))
    else:
        chrome_profile_dir = Path(args.chrome_profile_dir) if args.chrome_profile_dir else None
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
            chrome_profile_dir,
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
