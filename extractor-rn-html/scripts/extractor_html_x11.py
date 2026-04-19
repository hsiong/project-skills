#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import html
import json
import mimetypes
import os
import random
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import TypedDict
from urllib import error, parse, request

import numpy as np

USER_AGENT = "Mozilla/5.0"
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
SVG_BLOCK_RE = re.compile(r"<svg\b.*?</svg>", re.IGNORECASE | re.DOTALL)
DEFS_BLOCK_RE = re.compile(r"<defs\b.*?</defs>", re.IGNORECASE | re.DOTALL)
SYMBOL_BLOCK_RE = re.compile(r"<symbol\b.*?</symbol>", re.IGNORECASE | re.DOTALL)
INLINE_STYLE_ATTR_RE = re.compile(r"\sstyle\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
INLINE_EVENT_ATTR_RE = re.compile(r"\son[a-z0-9_-]+\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE | re.DOTALL)
AVATAR_ITEM_TAG_RE = re.compile(
	r"<[^>]*\bclass\s*=\s*(\"[^\"]*\bavatar-item\b[^\"]*\"|'[^']*\bavatar-item\b[^']*')[^>]*>",
	re.IGNORECASE | re.DOTALL
)
CLASS_ATTR_RE = re.compile(r"\sclass\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
TRIGGER_ATTR_RE = re.compile(r"\strigger\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
DATA_V_ATTR_RE = re.compile(r"\sdata-v-[a-z0-9_-]+\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
TARGET_ATTR_RE = re.compile(r"\starget\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
DATA_USER_ID_ATTR_RE = re.compile(r"\sdata-user-id\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
DATA_XSEC_TOKEN_ATTR_RE = re.compile(r"\sdata-xsec-token\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
DATA_XSEC_SOURCE_ATTR_RE = re.compile(r"\sdata-xsec-source\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
SELECTED_DISABLED_SEARCH_ATTR_RE = re.compile(
	r"\sselected-disabled-search\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL
)
ID_ATTR_RE = re.compile(r"\sid\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
TRACK_DATA_ATTR_RE = re.compile(r"\strack-data\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
POINTS_ATTR_RE = re.compile(r"\spoints\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE | re.DOTALL)
REMOVED_META_NAME_TAG_RE = re.compile(
	r"<meta\b[^>]*\bname\s*=\s*(\"(?:viewport|format-detection|mobileOptimized|HandheldFriendly|applicable-device|mobile-web-app-capable|apple-mobile-web-app-status-bar-style|shenma-site-verification|360-site-verification|sogou-site-verification|google-site-verification|baidu-site-verification|og:image)\"|'(?:viewport|format-detection|mobileOptimized|HandheldFriendly|applicable-device|mobile-web-app-capable|apple-mobile-web-app-status-bar-style|shenma-site-verification|360-site-verification|sogou-site-verification|google-site-verification|baidu-site-verification|og:image)')[^>]*>",
	re.IGNORECASE | re.DOTALL, )
CREATOR_SERVICE_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*创作服务\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*直播管理\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*电脑直播助手\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"</div>\s*</div>", re.IGNORECASE | re.DOTALL, )
PRO_SERVICE_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*专业号\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*推广合作\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*蒲公英\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*商家入驻\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"<li\b[^>]*>\s*<span\b[^>]*>\s*<a\b[^>]*>\s*MCN入驻\s*</a>\s*</span>\s*<span\b[^>]*>\s*</span>\s*</li>\s*"
	r"</div>\s*</div>", re.IGNORECASE | re.DOTALL, )
REPORT_COMMENT_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*<div\b[^>]*>\s*<div\b[^>]*>\s*<span\b[^>]*>\s*举报评论\s*</span>\s*</div>\s*</div>\s*</div>\s*</div>",
	re.IGNORECASE | re.DOTALL, )
NOTE_ACTION_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*"
	r"<div\b[^>]*>\s*下载图片\s*</div>\s*"
	r"<div\b[^>]*>\s*复制图片\s*</div>\s*"
	r"<div\b[^>]*>\s*复制笔记链接\s*</div>\s*"
	r"</div>", re.IGNORECASE | re.DOTALL, )
PRESERVED_MODEL_CLASS_NAMES = {"parent-comment"}
REPORT_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*<div\b[^>]*\bselected\s*=\s*(\"false\"|'false')[^>]*\bmultiselected\s*=\s*(\"false\"|'false')[^>]*>\s*"
	r"<div\b[^>]*>\s*<span\b[^>]*>\s*举报\s*</span>\s*</div>\s*</div>\s*</div>\s*</div>",
	re.IGNORECASE | re.DOTALL, )


class ChunkResult(TypedDict):
	title: str
	正文: str
	评论: str
	互动数据: str
	图片: list[str]
	视频: list[str]


ROOT_DIR: Path | None = None


def randomize_delay(base_seconds: float,
                    jitter_ratio: float = 0.35,
                    min_seconds: float = 0.01,
                    max_seconds: float | None = None, ) -> float:
	if base_seconds <= 0:
		return 0.0
	jitter = base_seconds * jitter_ratio
	delay_seconds = random.uniform(max(min_seconds, base_seconds - jitter), base_seconds + jitter)
	if max_seconds is not None:
		return min(max_seconds, delay_seconds)
	return delay_seconds


def sleep_randomized(base_seconds: float,
                     jitter_ratio: float = 0.35,
                     min_seconds: float = 0.01,
                     max_seconds: float | None = None, ) -> None:
	time.sleep(
		randomize_delay(base_seconds, jitter_ratio=jitter_ratio, min_seconds=min_seconds, max_seconds=max_seconds)
	)


def format_log_value(value: object) -> str:
	if isinstance(value, Path):
		return str(value)
	if isinstance(value, (str, int, float, bool)) or value is None:
		return json.dumps(value, ensure_ascii=False)
	return json.dumps(value, ensure_ascii=False, default=str)


def log_event(stage: str, is_error: bool = False, **kwargs: object) -> None:
	timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
	
	RESET = "\033[0m"
	if is_error:
		RED = "\033[31m" # MAGENTA
	else:
		RED = "\033[35m" # RED
		
	if kwargs:
		detail_text = ", ".join(f"{key}={format_log_value(value)}" for key, value in kwargs.items())
		print(f"[{timestamp}] {RED} [{stage}] {RESET} {detail_text}", flush=True)
		return
	print(f"[{timestamp}] [{stage}]", flush=True)


ACTIVITY_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*"
	r"<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*</div>\s*"
	r"<div\b[^>]*>\s*活动\s*</div>\s*"
	r"<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*</div>\s*"
	r"</div>\s*"
	r"<div\b[^>]*>\s*"
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*</div>\s*</div>\s*"
	r"<div\b[^>]*>\s*活动\s*</div>\s*"
	r"<div\b[^>]*>\s*"
	r"<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*</div>\s*"
	r"<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*"
	r"<button\b[^>]*>\s*<span\b[^>]*>\s*</span>\s*</button>\s*"
	r"</div>\s*</div>\s*"
	r"<iframe\b[^>]*>\s*</iframe>\s*</div>", re.IGNORECASE | re.DOTALL, )
ADBLOCK_TIPS_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*</div>\s*<div\b[^>]*>\s*"
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*温馨提示\s*</div>\s*</div>\s*"
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*您的浏览器似乎开启了广告屏蔽插件，可能对正常使用造成影响，请移除插件或将小红书加入插件白名单后继续使用。\s*</div>\s*</div>\s*"
	r"<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*<span\b[^>]*>\s*我知道了\s*</span>\s*</span>\s*</button>\s*</div>\s*"
	r"</div>\s*</div>", re.IGNORECASE | re.DOTALL, )
APPEAL_MODAL_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*</div>\s*<div\b[^>]*>\s*<div\b[^>]*>\s*</div>\s*<div\b[^>]*>\s*</div>\s*"
	r"<div\b[^>]*>\s*<button\b[^>]*>\s*<span\b[^>]*>\s*<span\b[^>]*>\s*我要申诉\s*</span>\s*</span>\s*</button>\s*"
	r"<button\b[^>]*>\s*<span\b[^>]*>\s*<span\b[^>]*>\s*我知道了\s*</span>\s*</span>\s*</button>\s*</div>\s*</div>\s*</div>",
	re.IGNORECASE | re.DOTALL, )
FOOTER_MORE_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*更多\s*</div>\s*<div\b[^>]*>.*?沪ICP备13030189号.*?©\s*2014-2026.*?行吟信息科技（上海）有限公司.*?地址：上海市黄浦区马当路388号C座.*?电话：9501-3888.*?</div>\s*</div>",
	re.IGNORECASE | re.DOTALL, )
BOTTOM_NAV_BLOCK_RE = re.compile(
	r"<div\b[^>]*>\s*<div\b[^>]*>\s*<ul\b[^>]*>.*?发现.*?直播.*?发布.*?通知.*?<span\b[^>]*>\s*我\s*</span>.*?沪ICP备13030189号.*?©\s*2014-2026.*?行吟信息科技（上海）有限公司.*?电话：9501-3888.*?</ul>\s*</div>\s*</div>",
	re.IGNORECASE | re.DOTALL, )
HEADER_SEARCH_BLOCK_RE = re.compile(
	r"<header\b[^>]*>.*?placeholder\s*=\s*(\"搜索小红书\"|'搜索小红书').*?placeholder\s*=\s*(\"搜索小红书\"|'搜索小红书').*?创作中心.*?业务合作.*?</header>\s*</div>",
	re.IGNORECASE | re.DOTALL, )
A_OPEN_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE | re.DOTALL)
A_CLOSE_TAG_RE = re.compile(r"</a>", re.IGNORECASE)
INTERTAG_WHITESPACE_RE = re.compile(r">\s+<", re.DOTALL)
LINEBREAK_RE = re.compile(r"[\r\n\t]+")
MULTISPACE_RE = re.compile(r" {2,}")
SHARE_COUNT_RE = re.compile(r'"shareCount"\s*:\s*"?(?P<count>\d+)"?', re.IGNORECASE)
MEDIA_SKIP_PATTERNS = ("avatar", "emoji", "icon", "logo", "sprite", "badge", "favicon",)


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
	result_summary: str
	precheck_status_code: int | None
	precheck_location: str
	stop_reason: str
	html_path: Path = None
	capture_error: bool = False
	parse_error: bool = False


@dataclass
class PrecheckResult:
	precheck_error: bool
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


@dataclass
class MediaCandidate:
	kind: str
	source: str
	resolved: str


class MediaCollector(HTMLParser):
	def __init__(self) -> None:
		super().__init__(convert_charrefs=True)
		self.image_refs: list[str] = []
		self.video_refs: list[str] = []
	
	def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		attr_map = {key.lower(): value or "" for key, value in attrs}
		lower_tag = tag.lower()
		if lower_tag == "img":
			self._append_image(attr_map.get("src"))
			self._append_image(attr_map.get("data-src"))
			self._append_image(first_srcset_url(attr_map.get("srcset", "")))
			return
		if lower_tag == "video":
			self._append_image(attr_map.get("poster"))
			self._append_video(attr_map.get("src"))
			return
		if lower_tag == "source":
			source_ref = attr_map.get("src", "")
			type_hint = attr_map.get("type", "").lower()
			if "video" in type_hint or looks_like_video_url(source_ref):
				self._append_video(source_ref)
			elif "image" in type_hint:
				self._append_image(source_ref)
			return
		if lower_tag != "meta":
			return
		prop = (attr_map.get("property") or attr_map.get("name") or "").lower()
		content = attr_map.get("content", "")
		if prop in {"og:image", "twitter:image", "twitter:image:src"}:
			self._append_image(content)
		elif prop in {"og:video", "og:video:url", "twitter:player"}:
			self._append_video(content)
	
	def _append_image(self, value: str | None) -> None:
		if value:
			self.image_refs.append(value)
	
	def _append_video(self, value: str | None) -> None:
		if value:
			self.video_refs.append(value)


class XSelectionEvent(ctypes.Structure):
	_fields_ = [("type", ctypes.c_int),
	            ("serial", ctypes.c_ulong),
	            ("send_event", ctypes.c_int),
	            ("display", ctypes.c_void_p),
	            ("requestor", ctypes.c_ulong),
	            ("selection", ctypes.c_ulong),
	            ("target", ctypes.c_ulong),
	            ("property", ctypes.c_ulong),
	            ("time", ctypes.c_ulong), ]


class XEvent(ctypes.Union):
	_fields_ = [("type", ctypes.c_int), ("xselection", XSelectionEvent), ("pad", ctypes.c_long * 24), ]


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
	return subprocess.run(
		cmd, check=check, text=True, capture_output=capture, )


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
				window_id=parts[0], desktop=parts[1], wm_class=parts[2], host=parts[3], title=parts[4], )
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


def choose_target_window(windows: list[ChromeWindow],
                         hint: str | None,
                         active_window_id: str | None,
                         before_ids: set[str]) -> ChromeWindow:
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
	sleep_randomized(1.0, jitter_ratio=0.3, min_seconds=0.6, max_seconds=1.5)


def spawn_background_process(command: list[str], *, env: dict[str, str] | None = None, stdout=None, stderr=None, ) -> \
		subprocess.Popen[bytes]:
	return subprocess.Popen(
		command,
		env=env,
		stdin=subprocess.DEVNULL,
		stdout=stdout if stdout is not None else subprocess.DEVNULL,
		stderr=stderr if stderr is not None else subprocess.DEVNULL,
		start_new_session=True,
		close_fds=True, )


def list_chrome_processes_for_profile(profile_dir: Path) -> list[ProcessMatch]:
	escaped_profile = re.escape(str(profile_dir))
	pattern = re.compile(
		rf"(^|.*/)(google-chrome|google-chrome-stable|chromium|chrome)(\s|$).*--user-data-dir(?:=|\s+){escaped_profile}(\s|$)"
	)
	return list_process_matches(pattern)


def terminate_processes(processes: list[ProcessMatch], wait_seconds: float = 5.0) -> None:
	for process in processes:
		try:
			os.kill(process.pid, 15)
		except OSError:
			continue
	deadline = time.time() + max(wait_seconds, 0.5)
	while time.time() < deadline:
		if all(not pid_is_alive(process.pid) for process in processes):
			return
		time.sleep(0.1)
	for process in processes:
		if not pid_is_alive(process.pid):
			continue
		try:
			os.kill(process.pid, 9)
		except OSError:
			continue


def cleanup_chrome_profile_singletons(profile_dir: Path) -> None:
	for name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
		(profile_dir / name).unlink(missing_ok=True)


def reset_stale_chrome_profile(profile_dir: Path) -> None:
	processes = list_chrome_processes_for_profile(profile_dir)
	if not processes:
		cleanup_chrome_profile_singletons(profile_dir)
		return
	log_event(
		"chrome.profile.reset",
		profile_dir=profile_dir,
		pids=[process.pid for process in processes],
	)
	terminate_processes(processes)
	cleanup_chrome_profile_singletons(profile_dir)
	sleep_randomized(0.5, jitter_ratio=0.3, min_seconds=0.2, max_seconds=0.9)


def open_url(url: str,
             *,
             new_window: bool = False,
             profile_dir: Path | None = None,
             env: dict[str, str] | None = None, ) -> None:
	chrome = shutil_which("google-chrome") or shutil_which("google-chrome-stable") or shutil_which("chromium")
	if not chrome:
		raise SystemExit("no Chrome/Chromium binary found")
	command = [chrome]
	if new_window:
		command.append("--new-window")
	if profile_dir is not None:
		profile_dir.mkdir(parents=True, exist_ok=True)
		if new_window:
			reset_stale_chrome_profile(profile_dir)
		command.extend(
			[f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check", ]
		)
	# CDP
	from cdp_x11 import CDP_DEBUG_PORT
	command.extend(
		[f"--remote-debugging-port={CDP_DEBUG_PORT}", "--remote-allow-origins=*", ]
	)
	command.append(url)
	spawn_background_process(command, env=env)


def relay_url_to_existing_browser(url: str, *, profile_dir: Path, env: dict[str, str] | None = None) -> bool:
	chrome = shutil_which("google-chrome") or shutil_which("google-chrome-stable") or shutil_which("chromium")
	if not chrome:
		raise SystemExit("no Chrome/Chromium binary found")
	command = [chrome, f"--user-data-dir={profile_dir}", "--new-tab", url]
	result = subprocess.run(
		command,
		env=env,
		check=False,
		stdin=subprocess.DEVNULL,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		close_fds=True,
	)
	log_event(
		"chrome.tab.relay",
		returncode=result.returncode,
		stdout=result.stdout.strip(),
		stderr=result.stderr.strip(),
	)
	return result.returncode == 0


def open_url_in_existing_window(window_id: str,
                                url: str,
                                *,
                                profile_dir: Path | None = None,
                                env: dict[str, str] | None = None, ) -> None:
	log_event("chrome.tab.open.start", window_id=window_id, url=url, profile_dir=profile_dir)
	activate_window(window_id)
	sleep_randomized(0.2, jitter_ratio=0.35, min_seconds=0.08, max_seconds=0.45)
	if profile_dir is not None and relay_url_to_existing_browser(url, profile_dir=profile_dir, env=env):
		log_event("chrome.tab.open.done", window_id=window_id, mode="browser-relay")
		return
	controller = XController()
	controller.press_key("Escape")
	sleep_randomized(0.3, jitter_ratio=0.4, min_seconds=0.12, max_seconds=0.6)
	key_combo(controller, ["Control_L"], "t")
	sleep_randomized(0.35, jitter_ratio=0.35, min_seconds=0.18, max_seconds=0.7)
	key_combo(controller, ["Control_L"], "l")
	sleep_randomized(0.15, jitter_ratio=0.4, min_seconds=0.05, max_seconds=0.35)
	type_text(controller, url)
	sleep_randomized(0.12, jitter_ratio=0.4, min_seconds=0.04, max_seconds=0.25)
	tap_key(controller, "Return")
	log_event("chrome.tab.open.done", window_id=window_id, mode="keyboard-fallback")


def save_window_screenshot(window_id: str, path: Path) -> None:
	xwd_path = path.with_suffix(".xwd")
	try:
		run(["xwd", "-silent", "-id", window_id, "-out", str(xwd_path)], capture=False)
		run(
			["ffmpeg", "-v", "error", "-y", "-f", "xwd_pipe", "-i", str(xwd_path), "-frames:v", "1", str(path), ],
			capture=False, )
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
	log_event("extract_urls.start", input_count=len(raw_inputs))
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
		log_event("extract_urls.empty", is_error=True)
		raise SystemExit("no URL found in input")
	log_event("extract_urls.done", url_count=len(urls))
	return urls


def first_srcset_url(value: str) -> str:
	if not value:
		return ""
	first_item = value.split(",", 1)[0].strip()
	return first_item.split()[0] if first_item else ""


def looks_like_video_url(value: str) -> bool:
	lowered = value.lower()
	return any(lowered.endswith(suffix) for suffix in (".mp4", ".webm", ".m3u8", ".mov"))


def looks_like_image_url(value: str) -> bool:
	lowered = value.lower()
	return any(lowered.endswith(suffix) for suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))


def build_ollama_url(base_url: str, api_path: str) -> str:
	return parse.urljoin(base_url.rstrip("/") + "/", api_path.lstrip("/"))


class RnOllamaClient:
	def __init__(self, base_url: str, api_path: str, model: str, timeout: float) -> None:
		self.base_url = base_url.rstrip("/")
		self.api_path = api_path
		self.model = model
		self.timeout = timeout
		self.url = build_ollama_url(self.base_url, self.api_path)
	
	def chat(self,
	         user_prompt: str,
	         *,
	         chunk_size: int = 30000,
	         system_prompt: str = "",
	         images: list[str] | None = None) -> str:
		log_event(
			"ollama.chat.start",
			model=self.model,
			endpoint=self.url,
			chunk_size=chunk_size,
			image_count=len(images or []), )
		messages: list[dict[str, object]] = []
		if system_prompt:
			messages.append({"role": "system", "content": system_prompt})
		user_message: dict[str, object] = {"role": "user", "content": user_prompt}
		if images:
			user_message["images"] = images
		messages.append(user_message)
		payload = {
			"model": self.model, "stream": False, "messages": messages, "options": {
				"num_ctx": chunk_size,  # 用满模型支持的 40K 窗口
				"num_predict": num_predict,  # 允许最多生成 8000 tokens（你可以按需调大/调小）
				"verbose": True,  # 输出详细信息
			}
		}
		body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		req = request.Request(
			f'{self.url}', data=body, headers={
				"Content-Type": "application/json", "Accept": "application/json",
			}, method="POST", )
		try:
			with request.urlopen(req, timeout=self.timeout) as response:
				raw_text = response.read().decode("utf-8", errors="replace")
		except error.HTTPError as exc:
			detail = exc.read().decode("utf-8", errors="replace")
			raise RuntimeError(f"ollama-compatible request failed: {exc.code} {detail}") from exc
		except error.URLError as exc:
			raise RuntimeError(f"ollama-compatible request failed: {exc}") from exc
		try:
			payload_obj = json.loads(raw_text)
		except json.JSONDecodeError as exc:
			raise RuntimeError(f"ollama-compatible response is not json: {raw_text[:400]}") from exc
		if isinstance(payload_obj, dict):
			message = payload_obj.get("message")
			if isinstance(message, dict):
				content = message.get("content")
				if isinstance(content, str):
					log_event("ollama.chat.done", model=self.model, content_length=len(content))
					return content
			response_text = payload_obj.get("response")
			if isinstance(response_text, str):
				log_event("ollama.chat.done", model=self.model, content_length=len(response_text))
				return response_text
		raise RuntimeError(f"unexpected ollama-compatible response: {raw_text[:400]}")


class NoRedirectHandler(request.HTTPRedirectHandler):
	def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
		return None


def precheck_url(url: str, timeout: float = 10.0) -> PrecheckResult:
	log_event("precheck.start", timeout=timeout)
	opener = request.build_opener(NoRedirectHandler)
	req = request.Request(
		url, method="HEAD", headers={
			"User-Agent": "Mozilla/5.0", "Accept": "*/*",
		}, )
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
		log_event("precheck.network_error", is_error=True)
		return PrecheckResult(
			precheck_error=False, status_code=None, location="", result_summary="", )
	except Exception:
		log_event("precheck.unknown_error", is_error=True)
		return PrecheckResult(
			precheck_error=False, status_code=None, location="", result_summary="", )
	if status_code == HTTPStatus.FOUND: # moved
		log_event("precheck.moved", status_code=status_code, location=location, is_error=True)
		return PrecheckResult(
			precheck_error=True, status_code=status_code, location=location, result_summary="页面已下架", )
	if status_code == HTTPStatus.NOT_FOUND and ("/404" in url or "/404" in location):
		log_event("precheck.NOT_FOUND", status_code=status_code, location=location, is_error=True)
		return PrecheckResult(
			precheck_error=True, status_code=status_code, location=location, result_summary="页面不存在", )
	log_event("precheck.done", status_code=status_code, location=location, skipped_capture=False)
	return PrecheckResult(
		precheck_error=False, status_code=status_code, location=location, result_summary="", )


def load_rgb_image(path: Path) -> np.ndarray:
	probe = run(
		["ffprobe",
		 "-v",
		 "error",
		 "-select_streams",
		 "v:0",
		 "-show_entries",
		 "stream=width,height",
		 "-of",
		 "csv=s=x:p=0",
		 str(path), ]
	)
	width_text, height_text = probe.stdout.strip().split("x")
	width = int(width_text)
	height = int(height_text)
	frame = subprocess.run(
		["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-", ],
		check=True,
		capture_output=True, )
	rgb = np.frombuffer(frame.stdout, dtype=np.uint8)
	return rgb.reshape((height, width, 3))


def sample_region(image: np.ndarray,
                  *,
                  x_start_ratio: float,
                  x_end_ratio: float,
                  y_start_ratio: float,
                  y_end_ratio: float,
                  sample_height: int = 72,
                  sample_width: int = 72, ) -> np.ndarray:
	height, width, _ = image.shape
	x0 = max(0, min(width - 1, int(width * x_start_ratio)))
	x1 = max(x0 + 1, min(width, int(width * x_end_ratio)))
	y0 = max(0, min(height - 1, int(height * y_start_ratio)))
	y1 = max(y0 + 1, min(height, int(height * y_end_ratio)))
	cropped = image[y0:y1, x0:x1]
	y_indices = np.linspace(0, cropped.shape[0] - 1, num=min(sample_height, cropped.shape[0]), dtype=int)
	x_indices = np.linspace(0, cropped.shape[1] - 1, num=min(sample_width, cropped.shape[1]), dtype=int)
	sampled = cropped[np.ix_(y_indices, x_indices)]
	grayscale = (sampled[:, :, 0].astype(np.float32) * 0.299 + sampled[:, :, 1].astype(np.float32) * 0.587 + sampled[
		:, :, 2].astype(np.float32) * 0.114)
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
	blue_mask = ((blue >= 85) & (blue - red >= 18) & (blue - green >= 6) & (green <= 190))
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
			merged[-1] = (min(prev_min_y, min_y),
			              max(prev_max_y, max_y),
			              min(prev_min_x, min_x),
			              max(prev_max_x, max_x),)
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
				occlusion_reason=occlusion_reason, )
		)
	return targets


class XController:
	def __init__(self) -> None:
		self.last_pointer_position: tuple[int, int] | None = None
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
		self.lib_x11.XWarpPointer.argtypes = [ctypes.c_void_p,
		                                      ctypes.c_ulong,
		                                      ctypes.c_ulong,
		                                      ctypes.c_int,
		                                      ctypes.c_int,
		                                      ctypes.c_uint,
		                                      ctypes.c_uint,
		                                      ctypes.c_int,
		                                      ctypes.c_int, ]
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

	def _warp_pointer_to(self, x: int, y: int) -> None:
		if self.backend == "python-xlib":
			self.root.warp_pointer(x, y)
			self.display.sync()
			self.last_pointer_position = (x, y)
			return
		self.lib_x11.XWarpPointer(self.display, 0, self.root, 0, 0, 0, 0, x, y)
		self.lib_x11.XFlush(self.display)
		self.lib_x11.XSync(self.display, 0)
		self.last_pointer_position = (x, y)

	def _pause_after_pointer_move(self, is_final_step: bool = False) -> None:
		if is_final_step:
			sleep_randomized(0.11, jitter_ratio=0.8, min_seconds=0.04, max_seconds=0.28)
			return
		sleep_randomized(0.06, jitter_ratio=0.95, min_seconds=0.02, max_seconds=0.18)
	
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
		start_x, start_y = self.last_pointer_position or (
			x + random.randint(-120, 120), y + random.randint(-90, 90)
		)
		distance = max(abs(x - start_x), abs(y - start_y))
		step_count = max(3, min(8, distance // 70 + random.randint(1, 3)))
		overshoot_x = x + random.randint(-6, 6)
		overshoot_y = y + random.randint(-4, 4)
		for step_index in range(1, step_count + 1):
			progress = step_index / step_count
			target_x = overshoot_x if step_index < step_count else x
			target_y = overshoot_y if step_index < step_count else y
			jitter_x = 0 if step_index == step_count else random.randint(-10, 10)
			jitter_y = 0 if step_index == step_count else random.randint(-8, 8)
			next_x = int(start_x + (target_x - start_x) * progress) + jitter_x
			next_y = int(start_y + (target_y - start_y) * progress) + jitter_y
			self._warp_pointer_to(next_x, next_y)
			self._pause_after_pointer_move(is_final_step=step_index == step_count)
		if random.random() < 0.35:
			settle_x = x + random.randint(-2, 2)
			settle_y = y + random.randint(-2, 2)
			self._warp_pointer_to(settle_x, settle_y)
			sleep_randomized(0.05, jitter_ratio=0.9, min_seconds=0.02, max_seconds=0.14)
			self._warp_pointer_to(x, y)
	
	def click(self, x: int, y: int) -> None:
		self.move_pointer(x, y)
		if self.backend == "python-xlib":
			sleep_randomized(0.28, jitter_ratio=0.7, min_seconds=0.12, max_seconds=0.65)
			self.xtest.fake_input(self.display, self.X.ButtonPress, 1)
			self.xtest.fake_input(self.display, self.X.ButtonRelease, 1)
			self.display.sync()
			sleep_randomized(0.09, jitter_ratio=0.8, min_seconds=0.03, max_seconds=0.24)
			return
		sleep_randomized(0.28, jitter_ratio=0.7, min_seconds=0.12, max_seconds=0.65)
		self.lib_xtst.XTestFakeButtonEvent(self.display, 1, 1, 0)
		self.lib_xtst.XTestFakeButtonEvent(self.display, 1, 0, 0)
		self.lib_x11.XSync(self.display, 0)
		sleep_randomized(0.09, jitter_ratio=0.8, min_seconds=0.03, max_seconds=0.24)
	
	def scroll_down(self, steps: int, x: int | None = None, y: int | None = None) -> None:
		if x is not None and y is not None:
			self.move_pointer(x, y)
		if self.backend == "python-xlib":
			for _ in range(steps):
				self.xtest.fake_input(self.display, self.X.ButtonPress, 5)
				self.xtest.fake_input(self.display, self.X.ButtonRelease, 5)
				self.display.sync()
				sleep_randomized(0.18, jitter_ratio=0.9, min_seconds=0.06, max_seconds=0.45)
				if random.random() < 0.2:
					sleep_randomized(0.3, jitter_ratio=0.85, min_seconds=0.12, max_seconds=0.72)
			return
		for _ in range(steps):
			self.lib_xtst.XTestFakeButtonEvent(self.display, 5, 1, 0)
			self.lib_xtst.XTestFakeButtonEvent(self.display, 5, 0, 0)
			self.lib_x11.XSync(self.display, 0)
			sleep_randomized(0.18, jitter_ratio=0.9, min_seconds=0.06, max_seconds=0.45)
			if random.random() < 0.2:
				sleep_randomized(0.3, jitter_ratio=0.85, min_seconds=0.12, max_seconds=0.72)
	
	def scroll_up(self, steps: int, x: int | None = None, y: int | None = None) -> None:
		if x is not None and y is not None:
			self.move_pointer(x, y)
		if self.backend == "python-xlib":
			for _ in range(steps):
				self.xtest.fake_input(self.display, self.X.ButtonPress, 4)
				self.xtest.fake_input(self.display, self.X.ButtonRelease, 4)
				self.display.sync()
				sleep_randomized(0.18, jitter_ratio=0.9, min_seconds=0.06, max_seconds=0.45)
				if random.random() < 0.2:
					sleep_randomized(0.3, jitter_ratio=0.85, min_seconds=0.12, max_seconds=0.72)
			return
		for _ in range(steps):
			self.lib_xtst.XTestFakeButtonEvent(self.display, 4, 1, 0)
			self.lib_xtst.XTestFakeButtonEvent(self.display, 4, 0, 0)
			self.lib_x11.XSync(self.display, 0)
			sleep_randomized(0.18, jitter_ratio=0.9, min_seconds=0.06, max_seconds=0.45)
			if random.random() < 0.2:
				sleep_randomized(0.3, jitter_ratio=0.85, min_seconds=0.12, max_seconds=0.72)


def comment_panel_point(geometry: dict[str, int], y_ratio: float = 0.72) -> tuple[int, int]:
	return (geometry["x"] + int(geometry["width"] * 0.87), geometry["y"] + int(geometry["height"] * y_ratio),)

def expand_visible_reply_links(window_id: str,
                               geometry: dict[str, int],
                               controller: XController,
                               screenshot_dir: Path,
                               screenshot_index: int, ) -> int:
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
			if any(
					abs(target.x - clicked_x) <= 14 and abs(target.y - clicked_y) <= 10 for clicked_x, clicked_y in
					click_targets
			):
				continue
			if any(
					abs(target.x - skipped_x) <= 20 and abs(target.y - skipped_y) <= 18 for skipped_x, skipped_y in
					skipped_targets
			):
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
			sleep_randomized(0.7, jitter_ratio=0.4, min_seconds=0.35, max_seconds=1.1)
			continue
		
		from cdp_x11 import cdp_click_expand_reply_near_target
		window = get_window_by_id(window_id)
		clicked, detail = cdp_click_expand_reply_near_target(
			next_target, geometry, window_title_hint=window.title if window else None, )
		log_event(
			"expand_reply.cdp_probe", target_x=next_target.x, target_y=next_target.y, clicked=clicked, detail=detail, )

		click_targets.append((next_target.x, next_target.y))
		attempts += 1
		sleep_randomized(0.9, jitter_ratio=0.4, min_seconds=0.45, max_seconds=1.45)
	probe_path.unlink(missing_ok=True)
	return len(click_targets)


COMMENT_PANEL_REGION = {
	"x_start_ratio": 0.63, "x_end_ratio": 0.98, "y_start_ratio": 0.24, "y_end_ratio": 0.96,
}

HEADER_REGION = {
	"x_start_ratio": 0.63, "x_end_ratio": 0.98, "y_start_ratio": 0.05, "y_end_ratio": 0.22,
}

MAIN_IMAGE_REGION = {
	"x_start_ratio": 0.05, "x_end_ratio": 0.58, "y_start_ratio": 0.12, "y_end_ratio": 0.90,
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
	return Path(__file__).resolve().parent / "tmp" / "xephyr_sessions"


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


@dataclass
class ProcessMatch:
	pid: int
	command: str


def list_process_matches(pattern: re.Pattern[str]) -> list[ProcessMatch]:
	result = run(["ps", "-eo", "pid=,args="], check=False)
	if result.returncode != 0:
		return []
	matches: list[ProcessMatch] = []
	for raw_line in result.stdout.splitlines():
		line = raw_line.strip()
		if not line:
			continue
		parts = line.split(None, 1)
		if len(parts) != 2 or not parts[0].isdigit():
			continue
		pid = int(parts[0])
		command = parts[1]
		if not pattern.search(command):
			continue
		matches.append(ProcessMatch(pid=pid, command=command))
	return matches


def build_multi_process_error(session_name: str,
                              process_label: str,
                              display_name: str,
                              matches: list[ProcessMatch]) -> str:
	lines = [f"multiple {process_label} processes matched session {session_name} on display {display_name}", ]
	for match in matches:
		lines.append(f"pid={match.pid} cmd={match.command}")
	lines.append("kill one of them and rerun, for example:")
	for match in matches:
		lines.append(f"kill {match.pid}")
	return "\n".join(lines)


def recover_session_state_from_processes(session_name: str, state: XephyrSessionState) -> XephyrSessionState | None:
	display_name = re.escape(state.display)
	xephyr_matches = list_process_matches(re.compile(rf"(^|.*/)Xephyr\s+{display_name}(\s|$)"))
	metacity_matches = list_process_matches(re.compile(rf"(^|.*/)metacity(\s|$).*--display\s+{display_name}(\s|$)"))
	if len(xephyr_matches) > 1:
		raise SystemExit(build_multi_process_error(session_name, "Xephyr", state.display, xephyr_matches))
	if len(metacity_matches) > 1:
		raise SystemExit(build_multi_process_error(session_name, "metacity", state.display, metacity_matches))
	if len(xephyr_matches) != 1 or len(metacity_matches) != 1:
		return None
	recovered_state = XephyrSessionState(
		name=state.name,
		display=state.display,
		screen=state.screen,
		profile_dir=state.profile_dir,
		xephyr_pid=xephyr_matches[0].pid,
		metacity_pid=metacity_matches[0].pid,
		created_at=state.created_at, )
	log_event(
		"xephyr.session.recovered",
		session_name=session_name,
		display=state.display,
		xephyr_pid=recovered_state.xephyr_pid,
		metacity_pid=recovered_state.metacity_pid, )
	write_session_state(session_name, recovered_state)
	return recovered_state


def load_session_state(session_name: str) -> XephyrSessionState | None:
	state_path = session_state_path(session_dir_for(session_name))
	if not state_path.exists():
		return None
	data = json.loads(state_path.read_text(encoding="utf-8"))
	state = XephyrSessionState(**data)
	if not (pid_is_alive(state.xephyr_pid) and pid_is_alive(state.metacity_pid)):
		recovered_state = recover_session_state_from_processes(session_name, state)
		if recovered_state is not None:
			return recovered_state
		state_path.unlink(missing_ok=True)
		return None
	return state


def write_session_state(session_name: str, state: XephyrSessionState) -> None:
	session_dir = session_dir_for(session_name)
	session_dir.mkdir(parents=True, exist_ok=True)
	session_state_path(session_dir).write_text(
		json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8"
	)


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
		["Xephyr", display_name, "-screen", screen, "-ac", "-br", ],
		stdin=subprocess.DEVNULL,
		stdout=xephyr_log,
		stderr=subprocess.STDOUT,
		start_new_session=True,
		close_fds=True, )
	try:
		wait_for_x_display(display_name)
		metacity = spawn_background_process(
			["metacity", "--display", display_name, "--sm-disable", ],
			env=display_env,
			stdout=metacity_log,
			stderr=subprocess.STDOUT, )
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
		created_at=time.strftime("%Y-%m-%d %H:%M:%S"), )
	write_session_state(session_name, state)
	return state


def effective_xephyr_session_name(args: argparse.Namespace) -> str:
	return sanitize_session_name(args.xephyr_session or "chrome-extractor-rn-main")


def ensure_xephyr_session(args: argparse.Namespace) -> tuple[XephyrSessionState, bool]:
	session_name = effective_xephyr_session_name(args)
	state = load_session_state(session_name)
	if state is not None:
		log_event(
			"xephyr.session.reuse",
			session_name=session_name,
			display=state.display,
			profile_dir=state.profile_dir
			)
		return state, False
	profile_dir = Path(args.chrome_profile_dir) if args.chrome_profile_dir else default_profile_dir_for_session(
		session_name
	)
	log_event(
		"xephyr.session.create",
		session_name=session_name,
		display=args.xephyr_display,
		screen=args.xephyr_screen,
		profile_dir=profile_dir, )
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
	log_event("xephyr.login_window.start", session_name=session_state.name, display=session_state.display)
	display_env = session_display_env(session_state.display)
	windows_before = list_chrome_windows()
	if windows_before:
		active_window_id = get_active_window_id()
		existing_window = choose_target_window(windows_before, None, active_window_id, set())
		log_event(
			"xephyr.login_window.reuse",
			session_name=session_state.name,
			window_id=existing_window.window_id,
			title=existing_window.title,
		)
		open_url_in_existing_window(
			existing_window.window_id,
			url,
			profile_dir=Path(session_state.profile_dir),
			env=display_env,
		)
	else:
		open_url(
			url, new_window=True, profile_dir=Path(session_state.profile_dir), env=display_env, )
	sleep_randomized(2.0, jitter_ratio=0.25, min_seconds=1.4, max_seconds=2.8)
	if not list_chrome_windows():
		raise SystemExit("failed to open Chrome inside Xephyr session")
	log_event("xephyr.login_window.done", session_name=session_state.name, had_windows=bool(windows_before))


def maybe_rerun_in_xephyr(args: argparse.Namespace) -> int | None:
	wants_xephyr = bool(args.inputs) or args.prepare_login or bool(args.close_xephyr_session) or args.xephyr or bool(
		args.xephyr_session
	)
	log_event(
		"xephyr.rerun.check",
		wants_xephyr=wants_xephyr,
		input_count=len(args.inputs),
		prepare_login=args.prepare_login,
		close_session=args.close_xephyr_session,
		current_display=os.environ.get("DISPLAY", ""), )
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
		log_event("xephyr.session.created_exit", session_name=session_state.name, display=session_state.display)
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
		log_event("xephyr.prepare_login.done", session_name=session_state.name, display=session_state.display)
		return 0
	if current_display == session_state.display:
		log_event("xephyr.rerun.skip", reason="already_in_session_display", display=current_display)
		return None
	rerun_args = [value for value in sys.argv[1:] if value != "--xephyr"]
	if "--prepare-login" in rerun_args:
		rerun_args.remove("--prepare-login")
	log_event("xephyr.rerun.exec", display=session_state.display, rerun_args=rerun_args)
	rerun = subprocess.run(
		[sys.executable, __file__, *rerun_args], env=session_display_env(session_state.display), check=False, )
	log_event("xephyr.rerun.done", returncode=rerun.returncode)
	return rerun.returncode


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
	sleep_randomized(0.03, jitter_ratio=0.5, min_seconds=0.01, max_seconds=0.06)
	key_event(controller, key_name, False)


def key_combo(controller: XController, modifiers: list[str], key_name: str) -> None:
	for modifier in modifiers:
		key_event(controller, modifier, True)
		sleep_randomized(0.02, jitter_ratio=0.5, min_seconds=0.01, max_seconds=0.05)
	tap_key(controller, key_name)
	sleep_randomized(0.02, jitter_ratio=0.5, min_seconds=0.01, max_seconds=0.05)
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
	for index, char in enumerate(text):
		key_name, use_shift = char_key(char)
		if use_shift:
			key_event(controller, "Shift_L", True)
		tap_key(controller, key_name)
		if use_shift:
			key_event(controller, "Shift_L", False)
		per_char_delay = delay_seconds * random.uniform(1.2, 2.4)
		if char in ":/?&=._-":
			per_char_delay *= random.uniform(1.2, 1.8)
		sleep_randomized(
			per_char_delay,
			jitter_ratio=0.95,
			min_seconds=0.012,
			max_seconds=max(0.16, per_char_delay * 3.2),
		)
		if index > 0 and index % 6 == 0 and random.random() < 0.28:
			sleep_randomized(0.22, jitter_ratio=0.9, min_seconds=0.08, max_seconds=0.58)


def read_clipboard_text(timeout_seconds: float = 5.0) -> str:
	lib_x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
	lib_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
	lib_x11.XOpenDisplay.restype = ctypes.c_void_p
	lib_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
	lib_x11.XDefaultRootWindow.restype = ctypes.c_ulong
	lib_x11.XCreateSimpleWindow.argtypes = [ctypes.c_void_p,
	                                        ctypes.c_ulong,
	                                        ctypes.c_int,
	                                        ctypes.c_int,
	                                        ctypes.c_uint,
	                                        ctypes.c_uint,
	                                        ctypes.c_uint,
	                                        ctypes.c_ulong,
	                                        ctypes.c_ulong, ]
	lib_x11.XCreateSimpleWindow.restype = ctypes.c_ulong
	lib_x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
	lib_x11.XInternAtom.restype = ctypes.c_ulong
	lib_x11.XConvertSelection.argtypes = [ctypes.c_void_p,
	                                      ctypes.c_ulong,
	                                      ctypes.c_ulong,
	                                      ctypes.c_ulong,
	                                      ctypes.c_ulong,
	                                      ctypes.c_ulong, ]
	lib_x11.XConvertSelection.restype = ctypes.c_int
	lib_x11.XPending.argtypes = [ctypes.c_void_p]
	lib_x11.XPending.restype = ctypes.c_int
	lib_x11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
	lib_x11.XNextEvent.restype = ctypes.c_int
	lib_x11.XGetWindowProperty.argtypes = [ctypes.c_void_p,
	                                       ctypes.c_ulong,
	                                       ctypes.c_ulong,
	                                       ctypes.c_long,
	                                       ctypes.c_long,
	                                       ctypes.c_int,
	                                       ctypes.c_ulong,
	                                       ctypes.POINTER(ctypes.c_ulong),
	                                       ctypes.POINTER(ctypes.c_int),
	                                       ctypes.POINTER(ctypes.c_ulong),
	                                       ctypes.POINTER(ctypes.c_ulong),
	                                       ctypes.POINTER(ctypes.c_void_p), ]
	lib_x11.XGetWindowProperty.restype = ctypes.c_int
	lib_x11.XDeleteProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong]
	lib_x11.XDeleteProperty.restype = ctypes.c_int
	lib_x11.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
	lib_x11.XDestroyWindow.restype = ctypes.c_int
	lib_x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
	lib_x11.XCloseDisplay.restype = ctypes.c_int
	lib_x11.XFlush.argtypes = [ctypes.c_void_p]
	lib_x11.XFlush.restype = ctypes.c_int
	lib_x11.XFree.argtypes = [ctypes.c_void_p]
	lib_x11.XFree.restype = ctypes.c_int
	
	display = lib_x11.XOpenDisplay(None)
	if not display:
		raise RuntimeError("failed to open X11 display for clipboard")
	
	window = ctypes.c_ulong(0)
	property_atom = ctypes.c_ulong(0)
	try:
		root = lib_x11.XDefaultRootWindow(display)
		window = ctypes.c_ulong(lib_x11.XCreateSimpleWindow(display, root, 0, 0, 1, 1, 0, 0, 0))
		if not window.value:
			raise RuntimeError("failed to create X11 window for clipboard")
		clipboard_atom = lib_x11.XInternAtom(display, b"CLIPBOARD", 0)
		utf8_atom = lib_x11.XInternAtom(display, b"UTF8_STRING", 0)
		string_atom = lib_x11.XInternAtom(display, b"STRING", 0)
		property_atom = ctypes.c_ulong(lib_x11.XInternAtom(display, b"CODEX_HTML_CLIPBOARD", 0))
		targets = [utf8_atom, string_atom]
		deadline = time.time() + timeout_seconds
		for target_atom in targets:
			lib_x11.XConvertSelection(display, clipboard_atom, target_atom, property_atom.value, window.value, 0)
			lib_x11.XFlush(display)
			while time.time() < deadline:
				if lib_x11.XPending(display) <= 0:
					time.sleep(0.05)
					continue
				event = XEvent()
				lib_x11.XNextEvent(display, ctypes.byref(event))
				if event.type != 31:
					continue
				if event.xselection.property == 0:
					break
				offset = 0
				chunks: list[bytes] = []
				while True:
					actual_type = ctypes.c_ulong()
					actual_format = ctypes.c_int()
					nitems = ctypes.c_ulong()
					bytes_after = ctypes.c_ulong()
					prop = ctypes.c_void_p()
					status = lib_x11.XGetWindowProperty(
						display,
						window.value,
						property_atom.value,
						offset,
						65536,
						0,
						0,
						ctypes.byref(actual_type),
						ctypes.byref(actual_format),
						ctypes.byref(nitems),
						ctypes.byref(bytes_after),
						ctypes.byref(prop), )
					if status != 0 or not prop.value:
						break
					if actual_format.value == 8:
						size = int(nitems.value)
					elif actual_format.value == 16:
						size = int(nitems.value) * 2
					else:
						size = int(nitems.value) * 4
					chunks.append(ctypes.string_at(prop, size))
					lib_x11.XFree(prop)
					if bytes_after.value == 0:
						break
					offset += max(1, size // 4)
				lib_x11.XDeleteProperty(display, window.value, property_atom.value)
				text = b"".join(chunks).decode("utf-8", errors="replace")
				if text:
					return text
		raise RuntimeError("clipboard did not return text")
	finally:
		if property_atom.value and window.value:
			lib_x11.XDeleteProperty(display, window.value, property_atom.value)
		if window.value:
			lib_x11.XDestroyWindow(display, window.value)
		lib_x11.XCloseDisplay(display)


def wait_for_clipboard_markers(start_marker: str, end_marker: str, timeout_seconds: float = 8.0) -> str:
	deadline = time.time() + timeout_seconds
	while time.time() < deadline:
		clipboard_text = read_clipboard_text(timeout_seconds=2.0)
		start_index = clipboard_text.find(start_marker)
		end_index = clipboard_text.rfind(end_marker)
		if start_index != -1 and end_index != -1 and end_index > start_index:
			return clipboard_text[start_index + len(start_marker): end_index].strip()
		time.sleep(0.2)
	raise RuntimeError("timed out waiting for HTML in clipboard")


def export_html_with_devtools_console(window_id: str, item_dir: Path) -> Path:
	controller = XController()
	start_marker = "__CODEX_HTML_BEGIN__"
	end_marker = "__CODEX_HTML_END__"
	command = (f"copy('{start_marker}\\n'+document.documentElement.outerHTML+'\\n{end_marker}')")
	activate_window(window_id)
	sleep_randomized(0.4, jitter_ratio=0.35, min_seconds=0.2, max_seconds=0.7)
	controller.press_key("Escape")
	sleep_randomized(0.2, jitter_ratio=0.4, min_seconds=0.08, max_seconds=0.4)
	key_combo(controller, ["Control_L", "Shift_L"], "j")
	sleep_randomized(1.2, jitter_ratio=0.35, min_seconds=0.7, max_seconds=1.8)
	key_combo(controller, ["Control_L"], "a")
	sleep_randomized(0.1, jitter_ratio=0.45, min_seconds=0.04, max_seconds=0.22)
	controller.press_key("BackSpace")
	sleep_randomized(0.1, jitter_ratio=0.45, min_seconds=0.04, max_seconds=0.22)
	type_text(controller, command)
	tap_key(controller, "Return")
	sleep_randomized(0.5, jitter_ratio=0.4, min_seconds=0.25, max_seconds=0.9)
	html_text = wait_for_clipboard_markers(start_marker, end_marker)
	key_combo(controller, ["Control_L", "Shift_L"], "j")
	html_path = item_dir / "expanded_page.html"
	html_path.write_text(html_text, encoding="utf-8")
	return html_path


def export_current_html(result: CaptureResult) -> Path:
	if result.window is None:
		raise RuntimeError("missing target chrome window")
	return export_html_with_devtools_console(result.window.window_id, result.item_dir)


def extract_share_count(raw_html: str) -> str:
	match = SHARE_COUNT_RE.search(raw_html)
	if not match:
		return ""
	return match.group("count").strip()


def clean_class_attr_for_model(match: re.Match[str]) -> str:
	quote_wrapped_value = match.group(1)
	quote = quote_wrapped_value[0]
	class_names = quote_wrapped_value[1:-1].split()
	preserved_class_names = [name for name in class_names if name in PRESERVED_MODEL_CLASS_NAMES]
	if not preserved_class_names:
		return ""
	return f" class={quote}{' '.join(preserved_class_names)}{quote}"


def clean_html_for_model(raw_html: str) -> tuple[str, str]:
	share_count = extract_share_count(raw_html)
	cleaned = HTML_COMMENT_RE.sub("", raw_html)
	cleaned = SVG_BLOCK_RE.sub("", cleaned)
	cleaned = DEFS_BLOCK_RE.sub("", cleaned)
	cleaned = SYMBOL_BLOCK_RE.sub("", cleaned)
	cleaned = SCRIPT_STYLE_RE.sub("", cleaned)
	cleaned = CREATOR_SERVICE_BLOCK_RE.sub("", cleaned)
	cleaned = PRO_SERVICE_BLOCK_RE.sub("", cleaned)
	cleaned = LINK_TAG_RE.sub("", cleaned)
	cleaned = AVATAR_ITEM_TAG_RE.sub("", cleaned)
	cleaned = CLASS_ATTR_RE.sub(clean_class_attr_for_model, cleaned)
	cleaned = TRIGGER_ATTR_RE.sub("", cleaned)
	cleaned = DATA_V_ATTR_RE.sub("", cleaned)
	cleaned = TARGET_ATTR_RE.sub("", cleaned)
	cleaned = DATA_USER_ID_ATTR_RE.sub("", cleaned)
	cleaned = DATA_XSEC_TOKEN_ATTR_RE.sub("", cleaned)
	cleaned = DATA_XSEC_SOURCE_ATTR_RE.sub("", cleaned)
	cleaned = SELECTED_DISABLED_SEARCH_ATTR_RE.sub("", cleaned)
	cleaned = ID_ATTR_RE.sub("", cleaned)
	cleaned = TRACK_DATA_ATTR_RE.sub("", cleaned)
	cleaned = POINTS_ATTR_RE.sub("", cleaned)
	cleaned = REMOVED_META_NAME_TAG_RE.sub("", cleaned)
	cleaned = INLINE_STYLE_ATTR_RE.sub("", cleaned)
	cleaned = INLINE_EVENT_ATTR_RE.sub("", cleaned)
	cleaned = REPORT_BLOCK_RE.sub("", cleaned)
	cleaned = ACTIVITY_BLOCK_RE.sub("", cleaned)
	cleaned = ADBLOCK_TIPS_BLOCK_RE.sub("", cleaned)
	cleaned = APPEAL_MODAL_BLOCK_RE.sub("", cleaned)
	cleaned = FOOTER_MORE_BLOCK_RE.sub("", cleaned)
	cleaned = BOTTOM_NAV_BLOCK_RE.sub("", cleaned)
	cleaned = HEADER_SEARCH_BLOCK_RE.sub("", cleaned)
	cleaned = A_OPEN_TAG_RE.sub("", cleaned)
	cleaned = A_CLOSE_TAG_RE.sub("", cleaned)
	cleaned = NOTE_ACTION_BLOCK_RE.sub("", cleaned)
	cleaned = REPORT_COMMENT_BLOCK_RE.sub("", cleaned)
	cleaned = INTERTAG_WHITESPACE_RE.sub("><", cleaned)
	cleaned = LINEBREAK_RE.sub("", cleaned)
	cleaned = MULTISPACE_RE.sub(" ", cleaned)
	return cleaned, share_count


def extract_json_object(raw_text: str) -> dict | None:
	candidates = [raw_text.strip()]
	fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw_text, re.DOTALL)
	if fenced_match:
		candidates.insert(0, fenced_match.group(1))
	start = raw_text.find("{")
	end = raw_text.rfind("}")
	if start != -1 and end != -1 and end > start:
		candidates.append(raw_text[start: end + 1])
	for candidate in candidates:
		if not candidate:
			continue
		try:
			parsed = json.loads(candidate)
		except json.JSONDecodeError:
			continue
		if isinstance(parsed, dict):
			return parsed
	return None


def normalize_text_field(value: object) -> str:
	if value is None:
		return ""
	if isinstance(value, list):
		return "\n".join(item for item in (normalize_text_field(item) for item in value) if item)
	if isinstance(value, dict):
		return json.dumps(value, ensure_ascii=False)
	return str(value).strip()


def split_html_chunks(html_text: str, chunk_size: int = 100000) -> list[str]:
	if len(html_text) <= chunk_size:
		return [html_text]
	return [html_text[index: index + chunk_size] for index in range(0, len(html_text), chunk_size)]


def merge_text_field(values: list[str]) -> str:
	merged: list[str] = []
	seen: set[str] = set()
	for value in values:
		text = value.strip()
		if not text or text in seen:
			continue
		seen.add(text)
		merged.append(text)
	return "\n".join(merged)


def normalize_media_list_field(value: object) -> list[str]:
	if value is None:
		return []
	if isinstance(value, list):
		result: list[str] = []
		for item in value:
			if item is None:
				continue
			text = str(item).strip()
			if text:
				result.append(text)
		return result
	text = str(value).strip()
	if not text:
		return []
	if "\n" in text:
		return [item.strip() for item in text.splitlines() if item.strip()]
	return [text]


def merge_media_list_field(values: list[list[str]]) -> list[str]:
	merged: list[str] = []
	seen: set[str] = set()
	for value_list in values:
		for value in value_list:
			text = value.strip()
			if not text or text in seen:
				continue
			seen.add(text)
			merged.append(text)
	return merged


def merge_interact_text_with_share_count(interact_text: str, share_count: str) -> str:
	text = interact_text.strip()
	count = share_count.strip()
	if not count:
		return text
	share_line = f"分享次数: {count}"
	if share_line in text:
		return text
	if text:
		return f"{text}\n{share_line}"
	return share_line


chunk_size = 20000
num_predict = 12000


def analyze_html_fields(html_text: str, page_url: str, client: RnOllamaClient, item_dir: Path) -> dict[str, object]:
	compact_html, share_count = clean_html_for_model(html_text)
	html_path = item_dir / 'expanded_page_analyse.html'
	html_path.write_text(compact_html, encoding="utf-8")
	
	html_chunks = split_html_chunks(compact_html, chunk_size=chunk_size)
	log_event(
		"analyze_html.start", html_length=len(compact_html), chunk_count=len(html_chunks), share_count=share_count, )
	system_prompt = """
    你只返回 JSON，不要解释，不要 markdown。请基于下面这份“评论已经展开后的整页 HTML 分段”提取结构化信息，必须返回 JSON 对象。

    要求：
   1. JSON 只包含这 6 个键：title、正文、评论、互动数据、图片、视频

   2. 结果尽量直接输出原文，不要润色

   3. 保留表情, 并且往往会有`<class="xxx-emoji">`标签的表情，请输出 ![emoji](emoji_url)

   4. `评论` 请按每个 parent-comment 输出为 markdown  blocks，作者需要标记出来，例如：

     parent-comment1 输出为
      ```
      - x:msg
          - ...可能多条
          - 可能 xx(作者):msg
          - ...可能多条
      ```
     parent-comment2 输出为
      ```
      - x:msg
          ...多条
      ```
     ...

   5. `图片`、`视频` 必须返回数组，值为笔记主体内容对应的原始媒体 url

   6. `图片`、`视频` 只保留笔记主体媒体，忽略 emoji、头像、icon、logo、装饰图、svg、data:image、按钮图、搜索框图

   7. `互动数据` 输出格式

         ```
         点赞: xx, 收藏: xx, 评论: xx
         ```

   8. 字段缺失时：

         - title、正文、评论、互动数据 返回空字符串
         - 图片、视频 返回空数组

    """
	chunk_results: list[ChunkResult] = []
	for index, html_chunk in enumerate(html_chunks, start=1):
		log_event("analyze_html.chunk.start", chunk_index=index, chunk_total=len(html_chunks))
		user_prompt = f"""
URL: {page_url}
当前分段: {index}/{len(html_chunks)}

HTML:
```html
{html_chunk}
```"""
		raw_text = client.chat(user_prompt, chunk_size=chunk_size, system_prompt=system_prompt)
		if not raw_text: # retry
			log_event("analyze_html.chunk.retry", chunk_index=index, system_prompt=system_prompt, is_error=True)
			raw_text = client.chat(user_prompt, chunk_size=chunk_size, system_prompt=system_prompt)
		parsed = extract_json_object(raw_text)
		if not parsed:
			log_event("analyze_html.chunk.failed", chunk_index=index, system_prompt=system_prompt, is_error=True)
			error_dict = {
				"system_prompt": system_prompt,
				"raw_text": raw_text
			}
			raise RuntimeError(json.dumps(error_dict, ensure_ascii=False))
		chunk_results.append(
			{
				"title": normalize_text_field(parsed.get("title")),
				"正文": normalize_text_field(parsed.get("正文")),
				"评论": normalize_text_field(parsed.get("评论")),
				"互动数据": normalize_text_field(parsed.get("互动数据")),
				"图片": normalize_media_list_field(parsed.get("图片")),
				"视频": normalize_media_list_field(parsed.get("视频")),
			}
		)
		log_event(
			"analyze_html.chunk.done",
			chunk_index=f'{item_dir}/chunk_{index}',
			image_count=len(chunk_results[-1]["图片"]),
			video_count=len(chunk_results[-1]["视频"]), )
	title = ""
	for chunk_result in chunk_results:
		if chunk_result["title"]:
			title = chunk_result["title"]
			break
	result = {
		"title": title,
		"正文": merge_text_field([item["正文"] for item in chunk_results]),
		"评论": merge_text_field([item["评论"] for item in chunk_results]),
		"互动数据": f'{merge_text_field([item["互动数据"] for item in chunk_results])}, 分享：{share_count}',
		"图片": merge_media_list_field([item["图片"] for item in chunk_results]),
		"视频": merge_media_list_field([item["视频"] for item in chunk_results]),
	}
	log_event(
		"analyze_html.done",
		title_found=bool(result["title"]),
		image_count=len(result["图片"]),
		video_count=len(result["视频"]), )
	return result


def resolve_media_reference(reference: str, page_url: str, html_path: Path) -> str:
	value = html.unescape(reference).strip()
	if not value or value.startswith("javascript:"):
		return ""
	if value.startswith("data:"):
		return value
	parsed_ref = parse.urlparse(value)
	if parsed_ref.scheme in {"http", "https"}:
		return value
	if parsed_ref.scheme == "file":
		return parse.unquote(parsed_ref.path)
	local_candidate = (html_path.parent / parse.unquote(value)).resolve()
	if local_candidate.exists():
		return str(local_candidate)
	return parse.urljoin(page_url, value)


def normalize_media_source(reference: str) -> str:
	return html.unescape(reference).strip()


def is_interesting_media(candidate: MediaCandidate) -> bool:
	lowered = candidate.resolved.lower()
	if any(marker in lowered for marker in MEDIA_SKIP_PATTERNS):
		return False
	if candidate.resolved.startswith("data:"):
		return True
	if candidate.kind == "image":
		return looks_like_image_url(lowered) or lowered.startswith("http")
	if candidate.kind == "video":
		return looks_like_image_url(lowered) or looks_like_video_url(lowered) or lowered.startswith("http")
	return False


def collect_media_candidates(html_text: str, page_url: str, html_path: Path) -> tuple[
	list[MediaCandidate], list[MediaCandidate]]:
	parser_obj = MediaCollector()
	parser_obj.feed(html_text)
	images: list[MediaCandidate] = []
	videos: list[MediaCandidate] = []
	seen: set[tuple[str, str]] = set()
	for kind, refs in (("image", parser_obj.image_refs), ("video", parser_obj.video_refs)):
		for ref in refs:
			resolved = resolve_media_reference(ref, page_url, html_path)
			if not resolved:
				continue
			candidate = MediaCandidate(kind=kind, source=ref, resolved=resolved)
			source_key = normalize_media_source(candidate.source)
			key = (candidate.kind, source_key if kind == "image" else candidate.resolved)
			if key in seen or not is_interesting_media(candidate):
				continue
			seen.add(key)
			if kind == "image":
				images.append(candidate)
			else:
				videos.append(candidate)
	return images, videos


def data_url_to_bytes(data_url: str) -> bytes:
	if ";base64," not in data_url:
		raise RuntimeError("unsupported data url without base64 payload")
	return base64.b64decode(data_url.split(",", 1)[1])


def guess_image_suffix(candidate: MediaCandidate) -> str:
	if candidate.resolved.startswith("data:"):
		mime_type = candidate.resolved.split(";", 1)[0][5:]
		return mimetypes.guess_extension(mime_type) or ".bin"
	parsed_url = parse.urlparse(candidate.resolved)
	suffix = Path(parse.unquote(parsed_url.path)).suffix
	return suffix if suffix else ".bin"


def read_media_bytes(reference: str, page_url: str, timeout_seconds: float = 20.0) -> bytes:
	if reference.startswith("data:"):
		return data_url_to_bytes(reference)
	local_path = Path(reference)
	if local_path.exists():
		return local_path.read_bytes()
	req = request.Request(
		reference, headers={
			"User-Agent": USER_AGENT, "Referer": page_url, "Accept": "*/*",
		}, )
	with request.urlopen(req, timeout=timeout_seconds) as response:
		return response.read()


def download_images(candidates: list[MediaCandidate], page_url: str, item_dir: Path, limit: int) -> list[str]:
	image_dir = item_dir / "images"
	image_dir.mkdir(parents=True, exist_ok=True)
	local_paths: list[str] = []
	seen_sources: set[str] = set()
	save_index = 1
	for candidate in candidates:
		source_key = normalize_media_source(candidate.source)
		if not source_key or source_key in seen_sources:
			continue
		seen_sources.add(source_key)
		if save_index > limit:
			break
		try:
			payload = read_media_bytes(candidate.resolved, page_url)
			suffix = guess_image_suffix(candidate)
			target_path = image_dir / f"image_{save_index:03d}{suffix}"
			target_path.write_bytes(payload)
			local_paths.append(str(target_path))
			save_index += 1
		except Exception:
			continue
	return local_paths


def collect_video_urls(candidates: list[MediaCandidate], limit: int) -> list[str]:
	urls: list[str] = []
	seen: set[str] = set()
	for candidate in candidates[:limit]:
		resolved = candidate.resolved.strip()
		if not resolved or resolved in seen:
			continue
		seen.add(resolved)
		urls.append(resolved)
	return urls


def build_manifest(result: CaptureResult,
		title: str = "",
		正文: str = "",
		评论: str = "",
		互动数据: str = "",
		图片: list[str] | None = None,
		视频: list[str] | None = None, ) -> dict[str, object]:
	return {
		"url": result.url,
		"item_index": result.index,
		"interaction_error": result.interaction_error,
		"result_summary": result.result_summary,
		"precheck_status_code": result.precheck_status_code,
		"stop_reason": result.stop_reason,
		"parse_error": result.parse_error,
		"title": title,
		"正文": 正文,
		"评论": 评论,
		"互动数据": 互动数据,
		"图片": 图片 or [],
		"视频": 视频 or [],
	}


def compact_manifest(manifest: dict[str, object]) -> dict[str, object]:
	return {key: value for key, value in manifest.items() if value not in ("", None, [], {})}


def write_manifest(manifest: dict[str, object], item_dir: Path) -> dict[str, object]:
	manifest = compact_manifest(manifest)
	(item_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
	return manifest


def process_result(result: CaptureResult,
                   client: RnOllamaClient,
                   *,
                   image_limit: int,
                   video_limit: int ) -> dict[str, object]:
	item_index = result.index
	log_event(
		"process_result.start",
		item_index=result.index,
		skipped_capture=result.capture_error,
		window_found=result.window is not None, )
	if result.capture_error or result.window is None:
		log_event("process_result.skip", item_index=result.index, reason=result.result_summary, is_error=True)
		return write_manifest(build_manifest(result), result.item_dir)
	try:
		html_path = result.html_path
		log_event(
			"process_result.html_exported", item_index=result.index, html_path=html_path)
		html_text = html_path.read_text(encoding="utf-8", errors="replace")
		if ROOT_DIR is None:
			raise RuntimeError("ROOT_DIR is not initialized")
		item_dir = ROOT_DIR / f"item_{item_index}"
		structured_fields = analyze_html_fields(html_text, result.url, client, item_dir)
		image_candidates = [MediaCandidate(kind="image", source=image_url, resolved=image_url) for image_url in
		                    structured_fields["图片"][:image_limit]]
		image_paths = download_images(image_candidates, result.url, result.item_dir, image_limit)
		video_urls = structured_fields["视频"][:video_limit]
		result.result_summary = "html exported"
		manifest = build_manifest(
			result,
			title=structured_fields["title"],
			正文=structured_fields["正文"],
			评论=structured_fields["评论"],
			互动数据=structured_fields["互动数据"],
			图片=image_paths,
			视频=video_urls, )
		log_event(
			"process_result.done", item_index=result.index, image_count=len(image_paths), video_count=len(video_urls), )
	except Exception as exc:  # noqa: BLE001
		result.result_summary = str(exc)
		result.parse_error = True
		manifest = build_manifest(result)
		log_event("process_result.error", item_index=result.index, error=str(exc), is_error=True)
	return write_manifest(manifest, result.item_dir)


def relative_path_text(path_value: str) -> str:
	if not path_value:
		return ""
	if ROOT_DIR is None:
		return path_value
	path = Path(path_value)
	try:
		return str(path.relative_to(ROOT_DIR))
	except ValueError:
		return str(path)


def format_multiline(value: object, empty_placeholder: str) -> list[str]:
	if value is None:
		return [empty_placeholder]
	if isinstance(value, list):
		if not value:
			return [empty_placeholder]
		return json.dumps(value, ensure_ascii=False, indent=2).splitlines()
	text = str(value).strip()
	return text.splitlines() if text else [empty_placeholder]


def build_report(manifests: list[dict[str, object]]) -> str:
	lines = ["# Chrome HTML Extraction Report", "", f"- Total items: {len(manifests)}", "", ]
	for manifest in manifests:
		lines.extend(
			[f"## Item {manifest.get('item_index')}",
			 "",
			 f"- URL: {manifest.get('url', '')}",
			 f"- Output dir: {relative_path_text(str(manifest.get('output_dir', ''))) or 'none'}",
			 f"- HTML: {relative_path_text(str(manifest.get('html_path', ''))) or 'none'}",
			 f"- Export method: {manifest.get('html_export_method', '') or 'none'}",
			 f"- Model: {manifest.get('ollama_model', '') or 'none'}",
			 f"- Endpoint: {manifest.get('ollama_endpoint', '') or 'none'}",
			 f"- Result: {manifest.get('result_summary', '') or 'pending'}", ]
		)
		if manifest.get("precheck_status_code") is not None:
			lines.append(f"- HTTP precheck: {manifest.get('precheck_status_code')}")
		if manifest.get("precheck_location"):
			lines.append(f"- Redirect location: {manifest.get('precheck_location')}")
		if manifest.get("stop_reason"):
			lines.append(f"- Stop reason: {manifest.get('stop_reason')}")
		if manifest.get("interaction_error"):
			lines.append(f"- Interaction error: {manifest.get('interaction_error')}")
		if manifest.get("parse_error"):
			lines.append(f"- Parse error: {manifest.get('parse_error')}")
		lines.extend(["", "### title", ""])
		lines.extend(format_multiline(manifest.get("title"), "(empty)"))
		lines.extend(["", "### 正文", ""])
		lines.extend(format_multiline(manifest.get("正文"), "(empty)"))
		lines.extend(["", "### 评论", ""])
		lines.extend(format_multiline(manifest.get("评论"), "(empty)"))
		lines.extend(["", "### 互动数据", ""])
		lines.extend(format_multiline(manifest.get("互动数据"), "(empty)"))
		lines.extend(["", "### 图片", ""])
		lines.extend(format_multiline(manifest.get("图片"), "[]"))
		lines.extend(["", "### 图片识别", ""])
		lines.extend(format_multiline(manifest.get("图片识别"), "[]"))
		lines.extend(["", "### 视频", ""])
		lines.extend(format_multiline(manifest.get("视频"), "[]"))
		lines.extend(["", ""])
	return "\n".join(lines)


def capture_item(url: str,
                 item_index: int,
                 wait_seconds: float,
                 window_hint: str,
                 skip_comment_scroll: bool,
                 max_pages: int,
                 scroll_steps: int,
                 chrome_profile_dir: Path | None, ) -> CaptureResult:
	log_event(
		"capture_item.start",
		item_index=item_index,
		wait_seconds=wait_seconds,
		max_pages=max_pages,
		scroll_steps=scroll_steps,
		chrome_profile_dir=chrome_profile_dir, )
	if ROOT_DIR is None:
		raise RuntimeError("ROOT_DIR is not initialized")
	item_dir = ROOT_DIR / f"item_{item_index}"
	item_dir.mkdir(parents=True, exist_ok=True)
	precheck = precheck_url(url)
	if precheck.precheck_error:
		log_event(
			"capture_item.precheck_skip", status_code=precheck.status_code, location=precheck.location, is_error=True)
		result = CaptureResult(
			index=item_index,
			url=url,
			item_dir=item_dir,
			window=None,
			screenshot_paths=[],
			interaction_error="",
			capture_error=True,
			result_summary=precheck.result_summary,
			parse_error=False,
			precheck_status_code=precheck.status_code,
			precheck_location=precheck.location,
			stop_reason="", )
		return result
	temp_capture_dir = item_dir / ".capture_tmp"
	temp_capture_dir.mkdir(parents=True, exist_ok=True)
	before_windows = list_chrome_windows()
	before_ids = {window.window_id for window in before_windows}
	active_window_id = get_active_window_id()
	existing_window: ChromeWindow | None = None
	controller: XController | None = None
	if before_windows:
		existing_window = choose_target_window(before_windows, window_hint or None, active_window_id, set())
		log_event(
			"capture_item.window.reuse",
			item_index=item_index,
			window_id=existing_window.window_id,
			title=existing_window.title
			)
		open_url_in_existing_window(
			existing_window.window_id,
			url,
			profile_dir=chrome_profile_dir,
			env=os.environ.copy(),
		)
	else:
		open_url(url, new_window=True, profile_dir=chrome_profile_dir)
	sleep_randomized(
		wait_seconds,
		jitter_ratio=0.2,
		min_seconds=max(0.6, wait_seconds * 0.7),
		max_seconds=max(wait_seconds + 1.2, wait_seconds * 1.3)
	)
	if existing_window is not None:
		refreshed_window = get_window_by_id(existing_window.window_id)
		target_window = refreshed_window or existing_window
	else:
		target_window = wait_for_target_window(before_ids, wait_seconds, window_hint or None)
		log_event(
			"capture_item.window.new",
			item_index=item_index,
			window_id=target_window.window_id,
			title=target_window.title
			)
	activate_window(target_window.window_id)
	screenshot_paths: list[Path] = []
	seen_hashes: set[str] = set()
	seen_comment_digests: set[str] = set()
	interaction_error = ""
	stop_reason = ""
	page_index = 0
	try:
		geometry = get_window_geometry(target_window.window_id)
		controller = controller or XController()
		controller.press_key("Escape")
		sleep_randomized(0.5, jitter_ratio=0.4, min_seconds=0.22, max_seconds=0.9)
		baseline_header_sample: np.ndarray | None = None
		previous_comment_sample: np.ndarray | None = None
		initial_title = target_window.title
		stagnant_rounds = 0
		tail_probe_rounds = 0
		while page_index < max_pages:
			log_event("capture_item.page.start", item_index=item_index, page_index=page_index + 1)
			# Try to expand replies
			expanded_count = expand_visible_reply_links(
				target_window.window_id, geometry, controller, temp_capture_dir, page_index + 1, )
			scroll_x, scroll_y = comment_panel_point(geometry)
			next_page = temp_capture_dir / f"_page_probe_{page_index + 1}.png"
			save_window_screenshot(target_window.window_id, next_page)
			current_window = get_window_by_id(target_window.window_id)
			if current_window is not None and initial_title and current_window.title != initial_title:
				stop_reason = f"warn:window title changed from '{initial_title}' to '{current_window.title}'"
				next_page.unlink(missing_ok=True)
				break
			image = load_rgb_image(next_page)
			header_sample = sample_region(image, **HEADER_REGION)
			if baseline_header_sample is None:
				baseline_header_sample = header_sample
			elif sample_distance(header_sample, baseline_header_sample) >= 4.5:
				stop_reason = "warn:page header changed, likely switched to a different note"
				next_page.unlink(missing_ok=True)
				break
			comment_sample = sample_region(image, **COMMENT_PANEL_REGION)
			if is_main_image_dominant(image):
				stop_reason = "warn:page focus moved to main image area"
				next_page.unlink(missing_ok=True)
				break
			comment_digest = sample_digest(comment_sample)
			if comment_digest in seen_comment_digests:
				if expanded_count == 0 and tail_probe_rounds < 3:
					tail_probe_rounds += 1
					next_page.unlink(missing_ok=True)
					controller.scroll_down(max(1, scroll_steps // 2), x=scroll_x, y=scroll_y)
					sleep_randomized(0.8, jitter_ratio=0.35, min_seconds=0.4, max_seconds=1.2)
					continue
				stop_reason = "ok:comment panel"
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
					sleep_randomized(0.8, jitter_ratio=0.35, min_seconds=0.4, max_seconds=1.2)
					continue
				stop_reason = "ok:comment panel"
				next_page.unlink(missing_ok=True)
				break
			next_hash = file_sha256(next_page)
			if next_hash in seen_hashes:
				if expanded_count == 0 and tail_probe_rounds < 3:
					tail_probe_rounds += 1
					next_page.unlink(missing_ok=True)
					controller.scroll_down(max(1, scroll_steps // 2), x=scroll_x, y=scroll_y)
					sleep_randomized(0.8, jitter_ratio=0.35, min_seconds=0.4, max_seconds=1.2)
					continue
				stop_reason = "ok:screenshot"
				next_page.unlink(missing_ok=True)
				break
			seen_hashes.add(next_hash)
			seen_comment_digests.add(comment_digest)
			previous_comment_sample = comment_sample
			tail_probe_rounds = 0
			page_index += 1
			log_event(
				"capture_item.page.done",
				item_index=item_index,
				page_index=page_index,
				expanded_count=expanded_count
				)
			next_page.unlink(missing_ok=True)
			if skip_comment_scroll:
				stop_reason = "ok:skip_comment_scroll"
				break
			controller.scroll_down(scroll_steps, x=scroll_x, y=scroll_y)
			sleep_randomized(1.2, jitter_ratio=0.35, min_seconds=0.7, max_seconds=1.8)
		if not stop_reason and page_index >= max_pages:
			stop_reason = f"limit:reached max_pages={max_pages}"
	except Exception as exc:  # noqa: BLE001
		interaction_error = str(exc)
		log_event("capture_item.error", item_index=item_index, error=interaction_error, is_error=True)
	finally:
		shutil.rmtree(temp_capture_dir, ignore_errors=True)
	log_event(
		"capture_item.done",
		item_index=item_index,
		stop_reason=stop_reason,
		interaction_error=interaction_error,
		page_count=page_index, )
	result = CaptureResult(
		index=item_index,
		url=url,
		item_dir=item_dir,
		window=target_window,
		screenshot_paths=screenshot_paths,
		interaction_error=interaction_error,
		capture_error=False,
		result_summary="",
		parse_error=False,
		precheck_status_code=precheck.status_code,
		precheck_location=precheck.location,
		stop_reason=stop_reason, )
	html_path = export_current_html(result)
	result.html_path = html_path
	return result


def main() -> int:
	global ROOT_DIR
	parser = argparse.ArgumentParser(
		description="Expand comments in GUI Chrome, export expanded HTML, and parse it with an Ollama-compatible model."
	)
	parser.add_argument("inputs", nargs="*", help="One or more URLs or raw text blocks containing URLs")
	parser.add_argument(
		"--out-dir", default="", help="Directory for html export, downloaded images, manifests, and report"
	)
	parser.add_argument("--wait-seconds", type=float, default=8.0, help="Wait after opening the URL")
	parser.add_argument("--window-hint", default="", help="Prefer a Chrome window whose title contains this text")
	parser.add_argument(
		"--skip-comment-scroll", action="store_true", help="Only capture the initial page before html export"
	)
	parser.add_argument("--max-pages", type=int, default=40, help="Maximum internal scan pages for one link")
	parser.add_argument("--scroll-steps", type=int, default=10, help="Mouse-wheel steps between screenshots")
	parser.add_argument("--chrome-profile-dir", default="", help="Use a dedicated Chrome profile directory")
	parser.add_argument(
		"--xephyr",
		action="store_true",
		help="Deprecated compatibility flag; capture now prefers the persistent chrome-extractor-rn-main Xephyr session by default"
	)
	parser.add_argument(
		"--xephyr-session",
		default="",
		help="Persistent Xephyr session name to reuse login state, defaulting to chrome-extractor-rn-main"
	)
	parser.add_argument("--xephyr-display", default=":99", help="Nested Xephyr display name")
	parser.add_argument("--xephyr-screen", default="1400x2200", help="Nested Xephyr screen size")
	parser.add_argument(
		"--prepare-login", action="store_true", help="Start or reuse a Xephyr session and open Chrome for manual login"
	)
	parser.add_argument("--login-url", default="", help="Optional URL to open while preparing login")
	parser.add_argument("--close-xephyr-session", default="", help="Close a persistent Xephyr session by name")
	parser.add_argument(
		"--ollama-base-url", default="http://127.0.0.1:11434", help="Base URL for the Ollama-compatible endpoint"
	)
	parser.add_argument(
		"--ollama-api-path", default="/api/chat", help="API path for the Ollama-compatible chat endpoint"
	)
	parser.add_argument("--ollama-model", default="gemma4:26b", help="Model name for the Ollama-compatible endpoint")
	parser.add_argument(
		"--ollama-timeout", type=float, default=180.0, help="Timeout for each Ollama-compatible request"
	)
	parser.add_argument("--image-limit", type=int, default=8, help="Maximum images to download")
	parser.add_argument("--video-limit", type=int, default=4, help="Maximum video urls to keep")
	args = parser.parse_args()
	log_event(
		"main.args",
		input_count=len(args.inputs),
		out_dir=args.out_dir,
		xephyr_session=args.xephyr_session,
		prepare_login=args.prepare_login,
		ollama_model=args.ollama_model,
		ollama_base_url=args.ollama_base_url, )
	
	rerun_code = maybe_rerun_in_xephyr(args)
	if rerun_code is not None:
		log_event("main.rerun_exit", rerun_code=rerun_code)
		return rerun_code
	
	require_binary("wmctrl")
	require_binary("xwininfo")
	require_binary("xwd")
	require_binary("xprop")
	require_binary("ffmpeg")
	require_binary("ffprobe")
	require_x11_session()
	log_event("main.environment_ready")
	
	if args.prepare_login or args.close_xephyr_session:
		return 0
	if not args.inputs:
		raise SystemExit("no URL found in input")
	timestamp = time.strftime("%Y%m%d_%H%M%S")
	out_dir = Path(args.out_dir) if args.out_dir else Path.cwd() / "tmp" / f"chrome_capture_v2_{timestamp}"
	out_dir.mkdir(parents=True, exist_ok=True)
	ROOT_DIR = out_dir
	wants_xephyr = bool(args.inputs) or args.prepare_login or args.xephyr or bool(args.xephyr_session)
	if wants_xephyr and not args.chrome_profile_dir:
		chrome_profile_dir = default_profile_dir_for_session(effective_xephyr_session_name(args))
	else:
		chrome_profile_dir = Path(args.chrome_profile_dir) if args.chrome_profile_dir else None
	client = RnOllamaClient(
		base_url=args.ollama_base_url,
		api_path=args.ollama_api_path,
		model=args.ollama_model,
		timeout=args.ollama_timeout, )
	urls = extract_urls(args.inputs)
	log_event("main.urls_ready", url_count=len(urls), out_dir=out_dir, chrome_profile_dir=chrome_profile_dir)
	results = [capture_item(
		url,
		index,
		args.wait_seconds,
		args.window_hint,
		args.skip_comment_scroll,
		args.max_pages,
		args.scroll_steps,
		chrome_profile_dir, ) for index, url in enumerate(urls, start=1)]
	log_event("main.capture_done", result_count=len(results))
	manifests = [process_result(
		result, client, image_limit=args.image_limit, video_limit=args.video_limit) for
		item_index, result in enumerate(results, start=1)]
	
	(out_dir / "RESULT.md").write_text(build_report(manifests), encoding="utf-8")
	log_event("main.report_done", manifest_count=len(manifests), report_path=out_dir / "RESULT.md")
	print(str(out_dir))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
