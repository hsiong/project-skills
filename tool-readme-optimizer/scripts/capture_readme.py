#!/usr/bin/env python3
"""Capture deterministic README screenshots and interaction recordings."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


ACTION_NAMES = {
    "check",
    "click",
    "drag_to",
    "fill",
    "hover",
    "press",
    "scroll_into_view",
    "select_option",
    "uncheck",
    "wait",
    "wait_for",
}

VISUAL_RESOURCE_PROPERTIES = (
    "background-image",
    "border-image-source",
    "content",
    "list-style-image",
    "mask-image",
    "-webkit-mask-image",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture README screenshots and recordings from a JSON configuration."
    )
    parser.add_argument("config", type=Path, help="Path to the capture JSON file")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)

    if not isinstance(config, dict):
        raise ValueError("capture config must be a JSON object")
    if not isinstance(config.get("base_url"), str):
        raise ValueError("base_url must be a string")

    captures = config.get("captures")
    shots = config.get("shots")
    if captures is not None and shots is not None:
        raise ValueError("use captures or the legacy shots field, not both")
    if captures is None:
        captures = shots
    if not isinstance(captures, list) or not captures:
        raise ValueError("captures must be a non-empty list")

    config["captures"] = captures
    return config


def positive_int(value: Any, label: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return parsed


def merged_capture(defaults: dict[str, Any], capture: Any) -> dict[str, Any]:
    if not isinstance(capture, dict):
        raise ValueError("each capture must be an object")

    merged = {**defaults, **capture}
    if not isinstance(merged.get("name"), str) or not merged["name"].strip():
        raise ValueError("each capture needs a non-empty name")

    kind = merged.get("kind", "screenshot")
    if kind not in {"screenshot", "recording"}:
        raise ValueError("capture kind must be screenshot or recording")
    merged["kind"] = kind

    actions = merged.get("actions", [])
    if not isinstance(actions, list):
        raise ValueError("actions must be a list")

    if kind == "recording":
        if Path(merged["name"]).suffix.lower() != ".webm":
            raise ValueError("recording names must end in .webm")
        poster = merged.get("poster")
        if poster is not None and (not isinstance(poster, str) or not poster.strip()):
            raise ValueError("poster must be a non-empty path")
        gif = merged.get("gif")
        if gif is not None and (
            not isinstance(gif, str) or Path(gif).suffix.lower() != ".gif"
        ):
            raise ValueError("gif must be a path ending in .gif")

        asset_names = [name for name in (merged["name"], poster, gif) if name]
        if len(asset_names) != len(set(asset_names)):
            raise ValueError("recording, poster, and gif paths must be different")

    return merged


def output_path(output_dir: Path, name: str) -> Path:
    base = output_dir.resolve()
    candidate = (base / name).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"capture name escapes output_dir: {name}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def viewport_for(capture: dict[str, Any]) -> dict[str, int]:
    viewport = capture.get("viewport", {"width": 1440, "height": 900})
    if not isinstance(viewport, dict):
        raise ValueError("viewport must be an object")
    return {
        "width": positive_int(viewport.get("width", 1440), "viewport width"),
        "height": positive_int(viewport.get("height", 900), "viewport height"),
    }


def require_selector(action: dict[str, Any], label: str = "selector") -> str:
    selector = action.get(label)
    if not isinstance(selector, str) or not selector.strip():
        raise ValueError(f"{action.get('action', 'action')} needs a non-empty {label}")
    return selector


async def run_actions(page: Any, capture: dict[str, Any]) -> None:
    default_pause = capture.get(
        "action_pause_ms", 250 if capture["kind"] == "recording" else 0
    )
    default_pause = positive_int(default_pause, "action_pause_ms", minimum=0)

    for index, raw_action in enumerate(capture.get("actions", []), start=1):
        if not isinstance(raw_action, dict):
            raise ValueError(f"action {index} must be an object")
        action_name = raw_action.get("action")
        if action_name not in ACTION_NAMES:
            raise ValueError(f"action {index} has unsupported action: {action_name}")

        timeout = positive_int(
            raw_action.get("timeout_ms", capture.get("timeout_ms", 30_000)),
            f"action {index} timeout_ms",
        )

        if action_name == "wait":
            await page.wait_for_timeout(
                positive_int(raw_action.get("ms"), f"action {index} ms", minimum=0)
            )
        elif action_name == "wait_for":
            await page.locator(require_selector(raw_action)).wait_for(
                state=raw_action.get("state", "visible"), timeout=timeout
            )
        else:
            selector = require_selector(raw_action)
            locator = page.locator(selector)
            if action_name == "click":
                await locator.click(timeout=timeout)
            elif action_name == "fill":
                if "value" not in raw_action:
                    raise ValueError(f"action {index} fill needs value")
                await locator.fill(str(raw_action["value"]), timeout=timeout)
            elif action_name == "press":
                key = raw_action.get("key")
                if not isinstance(key, str) or not key:
                    raise ValueError(f"action {index} press needs key")
                await locator.press(key, timeout=timeout)
            elif action_name == "hover":
                await locator.hover(timeout=timeout)
            elif action_name == "check":
                await locator.check(timeout=timeout)
            elif action_name == "uncheck":
                await locator.uncheck(timeout=timeout)
            elif action_name == "select_option":
                if "value" not in raw_action:
                    raise ValueError(f"action {index} select_option needs value")
                await locator.select_option(str(raw_action["value"]), timeout=timeout)
            elif action_name == "drag_to":
                target = page.locator(require_selector(raw_action, "target"))
                await locator.drag_to(target, timeout=timeout)
            elif action_name == "scroll_into_view":
                await locator.scroll_into_view_if_needed(timeout=timeout)

        pause = positive_int(
            raw_action.get("pause_after_ms", default_pause),
            f"action {index} pause_after_ms",
            minimum=0,
        )
        if pause:
            await page.wait_for_timeout(pause)


async def install_routes(page: Any, capture: dict[str, Any]) -> None:
    """Fulfill deterministic demo requests before the product page loads."""
    routes = capture.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("routes must be a list")

    for index, route_config in enumerate(routes, start=1):
        if not isinstance(route_config, dict):
            raise ValueError(f"route {index} must be an object")
        url_pattern = route_config.get("url")
        if not isinstance(url_pattern, str) or not url_pattern.strip():
            raise ValueError(f"route {index} needs a non-empty url")
        if "json" in route_config and "body" in route_config:
            raise ValueError(f"route {index} must use json or body, not both")

        method = route_config.get("method")
        if method is not None and (not isinstance(method, str) or not method.strip()):
            raise ValueError(f"route {index} method must be a non-empty string")

        status = positive_int(route_config.get("status", 200), f"route {index} status")
        if status > 599:
            raise ValueError(f"route {index} status must not exceed 599")

        headers = route_config.get("headers", {})
        if not isinstance(headers, dict):
            raise ValueError(f"route {index} headers must be an object")
        normalized_headers = {str(key): str(value) for key, value in headers.items()}

        body = route_config.get("body", "")
        content_type = route_config.get("content_type", "text/plain; charset=utf-8")
        if "json" in route_config:
            body = json.dumps(route_config["json"], ensure_ascii=False)
            content_type = route_config.get(
                "content_type", "application/json; charset=utf-8"
            )
        if not isinstance(body, str):
            raise ValueError(f"route {index} body must be a string")
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValueError(f"route {index} content_type must be a non-empty string")

        async def fulfill_route(
            route: Any,
            request: Any,
            *,
            expected_method: str | None = method,
            response_status: int = status,
            response_headers: dict[str, str] = normalized_headers,
            response_body: str = body,
            response_content_type: str = content_type,
        ) -> None:
            """Fulfill matching methods and let unrelated requests continue."""
            if expected_method and request.method.upper() != expected_method.upper():
                await route.continue_()
                return
            await route.fulfill(
                status=response_status,
                headers=response_headers,
                content_type=response_content_type,
                body=response_body,
            )

        await page.route(url_pattern, fulfill_route)


def optional_bool(value: Any, label: str, *, default: bool) -> bool:
    """Validate an optional boolean while preserving a documented default."""
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be true or false")
    return value


def summarize_urls(urls: list[str], *, limit: int = 5) -> str:
    """Keep failed-resource diagnostics readable when many URLs are involved."""
    shown = urls[:limit]
    suffix = f" (+{len(urls) - limit} more)" if len(urls) > limit else ""
    return ", ".join(shown) + suffix


async def wait_for_visual_assets(page: Any, capture: dict[str, Any]) -> None:
    """Wait for browser-managed visual resources and reject failed image loads."""
    timeout = positive_int(capture.get("timeout_ms", 30_000), "timeout_ms")

    if optional_bool(
        capture.get("wait_for_network_idle"),
        "wait_for_network_idle",
        default=True,
    ):
        await page.wait_for_load_state("networkidle", timeout=timeout)

    if optional_bool(
        capture.get("wait_for_stylesheets"),
        "wait_for_stylesheets",
        default=True,
    ):
        await page.wait_for_function(
            """() => Array.from(document.querySelectorAll('link[rel~="stylesheet"]'))
                .every(link => Boolean(link.sheet))""",
            timeout=timeout,
        )

    if optional_bool(capture.get("wait_for_fonts"), "wait_for_fonts", default=True):
        await page.wait_for_function(
            "() => !document.fonts || document.fonts.status === 'loaded'",
            timeout=timeout,
        )

    if optional_bool(capture.get("wait_for_images"), "wait_for_images", default=True):
        await page.wait_for_function(
            "() => Array.from(document.images).every(image => image.complete)",
            timeout=timeout,
        )
        failed_images = await page.evaluate(
            """() => Array.from(document.images)
                .filter(image => image.naturalWidth === 0)
                .map(image => image.currentSrc || image.src || '<missing src>')"""
        )
        if failed_images:
            raise RuntimeError(
                "visual verification failed; DOM images did not load: "
                f"{summarize_urls(failed_images)}"
            )

    if optional_bool(
        capture.get("wait_for_background_images"),
        "wait_for_background_images",
        default=True,
    ):
        # CSS image URLs are not represented by document.images, so inspect the
        # rendered styles for elements and pseudo-elements separately.
        resource_urls = await page.evaluate(
            """properties => {
                const urls = new Set();
                const collect = style => {
                    for (const property of properties) {
                        const value = style.getPropertyValue(property);
                        const pattern = /url\\(\\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*?))\\s*\\)/g;
                        for (const match of value.matchAll(pattern)) {
                            const raw = (match[1] || match[2] || match[3] || '').trim();
                            if (raw) urls.add(new URL(raw, document.baseURI).href);
                        }
                    }
                };
                for (const element of document.querySelectorAll('*')) {
                    collect(getComputedStyle(element));
                    collect(getComputedStyle(element, '::before'));
                    collect(getComputedStyle(element, '::after'));
                }
                return Array.from(urls);
            }""",
            VISUAL_RESOURCE_PROPERTIES,
        )
        failed_backgrounds = await page.evaluate(
            """urls => Promise.all(urls.map(url => new Promise(resolve => {
                const image = new Image();
                const finish = ok => resolve(ok ? null : url);
                image.onload = () => finish(image.naturalWidth > 0);
                image.onerror = () => finish(false);
                image.src = url;
                if (image.complete) finish(image.naturalWidth > 0);
            }))).then(results => results.filter(Boolean))""",
            resource_urls,
        )
        if failed_backgrounds:
            raise RuntimeError(
                "visual verification failed; CSS image resources did not load: "
                f"{summarize_urls(failed_backgrounds)}"
            )

    await page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => "
        "requestAnimationFrame(resolve)))"
    )


async def run_style_checks(page: Any, capture: dict[str, Any]) -> None:
    """Assert product-specific computed styles before an asset can be written."""
    checks = capture.get("style_checks", [])
    if not isinstance(checks, list):
        raise ValueError("style_checks must be a list")

    minimum_checks = positive_int(
        capture.get("minimum_style_checks", 2),
        "minimum_style_checks",
        minimum=0,
    )
    if len(checks) < minimum_checks:
        raise ValueError(
            f"style_checks needs at least {minimum_checks} entries; "
            "set minimum_style_checks explicitly only for a surface without "
            "meaningful computed CSS"
        )

    timeout = positive_int(capture.get("timeout_ms", 30_000), "timeout_ms")
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            raise ValueError(f"style check {index} must be an object")
        selector = require_selector(check)
        property_name = check.get("property")
        if not isinstance(property_name, str) or not property_name.strip():
            raise ValueError(f"style check {index} needs a non-empty property")

        expectations = [
            key for key in ("equals", "not_equals", "contains") if key in check
        ]
        if len(expectations) != 1:
            raise ValueError(
                f"style check {index} needs exactly one of equals, not_equals, or contains"
            )

        locator = page.locator(selector).first
        await locator.wait_for(state="attached", timeout=timeout)
        actual = await locator.evaluate(
            "(element, propertyName) => "
            "getComputedStyle(element).getPropertyValue(propertyName).trim()",
            property_name,
        )
        expectation = expectations[0]
        expected = str(check[expectation])
        passed = {
            "equals": actual == expected,
            "not_equals": actual != expected,
            "contains": expected in actual,
        }[expectation]
        if not passed:
            raise RuntimeError(
                f"style check {index} failed for {selector} ({property_name}): "
                f"expected {expectation} {expected!r}, got {actual!r}"
            )


async def prepare_page(page: Any, capture: dict[str, Any], base_url: str) -> None:
    target = capture.get("url") or urljoin(
        base_url, str(capture.get("path", "/")).lstrip("/")
    )
    await page.goto(
        target,
        wait_until=capture.get("wait_until", "domcontentloaded"),
        timeout=positive_int(capture.get("timeout_ms", 30_000), "timeout_ms"),
    )

    wait_for = capture.get("wait_for")
    if wait_for:
        if not isinstance(wait_for, str):
            raise ValueError("wait_for must be a CSS selector")
        await page.locator(wait_for).wait_for(
            state="visible",
            timeout=positive_int(capture.get("timeout_ms", 30_000), "timeout_ms"),
        )

    wait_ms = positive_int(capture.get("wait_ms", 0), "wait_ms", minimum=0)
    if wait_ms:
        await page.wait_for_timeout(wait_ms)

    hide = capture.get("hide", [])
    if not isinstance(hide, list):
        raise ValueError("hide must be a list of CSS selectors")
    for selector in hide:
        await page.locator(str(selector)).evaluate_all(
            "elements => elements.forEach(element => "
            "element.style.visibility = 'hidden')"
        )

    await run_actions(page, capture)
    await wait_for_visual_assets(page, capture)
    await run_style_checks(page, capture)

    tail_ms = positive_int(
        capture.get("tail_ms", 400 if capture["kind"] == "recording" else 0),
        "tail_ms",
        minimum=0,
    )
    if tail_ms:
        await page.wait_for_timeout(tail_ms)


async def take_screenshot(
    page: Any,
    destination: Path,
    capture: dict[str, Any],
    *,
    poster: bool = False,
) -> None:
    screenshot_options = {
        "path": str(destination),
        "animations": "disabled",
    }
    selector = capture.get("poster_selector") if poster else capture.get("selector")
    if poster and not selector:
        selector = capture.get("selector")
    if selector:
        await page.locator(str(selector)).screenshot(**screenshot_options)
    else:
        await page.screenshot(
            **screenshot_options,
            full_page=bool(capture.get("full_page", False)) if not poster else False,
        )


async def make_gif(source: Path, destination: Path, options: dict[str, Any]) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required when a recording requests a GIF")
    if not isinstance(options, dict):
        raise ValueError("gif_options must be an object")

    fps = positive_int(options.get("fps", 12), "gif fps")
    if fps > 30:
        raise ValueError("gif fps must not exceed 30")
    width = positive_int(options.get("width", 960), "gif width")
    colors = positive_int(options.get("colors", 128), "gif colors", minimum=2)
    if colors > 256:
        raise ValueError("gif colors must not exceed 256")

    start_ms = positive_int(options.get("start_ms", 0), "gif start_ms", minimum=0)
    duration_ms = options.get("duration_ms")
    if duration_ms is not None:
        duration_ms = positive_int(duration_ms, "gif duration_ms")

    filters = (
        f"fps={fps},scale=w='min({width},iw)':h=-2:flags=lanczos,"
        "split[s0][s1];"
        f"[s0]palettegen=max_colors={colors}:stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=3"
    )
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if start_ms:
        command.extend(["-ss", f"{start_ms / 1000:.3f}"])
    command.extend(["-i", str(source)])
    if duration_ms is not None:
        command.extend(["-t", f"{duration_ms / 1000:.3f}"])
    command.extend(["-an", "-filter_complex", filters, "-loop", "0", str(destination)])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode:
        destination.unlink(missing_ok=True)
        detail = stderr.decode(errors="replace").strip().splitlines()
        message = detail[-1] if detail else "unknown FFmpeg error"
        raise RuntimeError(f"could not create {destination}: {message}")


async def capture_screenshot(
    browser: Any,
    capture: dict[str, Any],
    base_url: str,
    output_dir: Path,
) -> None:
    viewport = viewport_for(capture)
    context = await browser.new_context(
        viewport=viewport,
        color_scheme=capture.get("color_scheme", "dark"),
        device_scale_factor=float(capture.get("device_scale_factor", 1)),
    )
    page = await context.new_page()
    destination = output_path(output_dir, capture["name"])
    try:
        await install_routes(page, capture)
        await prepare_page(page, capture, base_url)
        await take_screenshot(page, destination, capture)
    finally:
        await context.close()
    print(destination)


async def capture_recording(
    browser: Any,
    capture: dict[str, Any],
    base_url: str,
    output_dir: Path,
) -> None:
    viewport = viewport_for(capture)
    destination = output_path(output_dir, capture["name"])
    poster = (
        output_path(output_dir, capture["poster"]) if capture.get("poster") else None
    )

    with tempfile.TemporaryDirectory(prefix="readme-recording-") as recording_dir:
        context = await browser.new_context(
            viewport=viewport,
            color_scheme=capture.get("color_scheme", "dark"),
            device_scale_factor=float(capture.get("device_scale_factor", 1)),
            record_video_dir=recording_dir,
            record_video_size=viewport,
        )
        page = await context.new_page()
        video = page.video
        succeeded = False
        try:
            await install_routes(page, capture)
            await prepare_page(page, capture, base_url)
            if poster:
                await take_screenshot(page, poster, capture, poster=True)
            succeeded = True
        finally:
            if not page.is_closed():
                await page.close()
            try:
                if succeeded:
                    if video is None:
                        raise RuntimeError("Playwright did not create a video")
                    await video.save_as(destination)
            finally:
                await context.close()

    print(destination)
    if poster:
        print(poster)

    if capture.get("gif"):
        gif = output_path(output_dir, capture["gif"])
        await make_gif(destination, gif, capture.get("gif_options", {}))
        print(gif)


async def capture(config: dict[str, Any]) -> None:
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Python Playwright is required. In an isolated environment run: "
            "python -m pip install -r /path/to/tool-readme-optimizer/requirements.txt && "
            "python -m playwright install chromium ffmpeg"
        ) from exc

    defaults = config.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be an object")

    captures = [
        merged_capture(defaults, raw_capture) for raw_capture in config["captures"]
    ]
    base_url = config["base_url"].rstrip("/") + "/"
    output_dir = Path(config.get("output_dir", "docs/images/readme"))

    browser_channel = config.get("browser_channel")
    if browser_channel is not None and (
        not isinstance(browser_channel, str) or not browser_channel.strip()
    ):
        raise ValueError("browser_channel must be a non-empty string")

    try:
        async with async_playwright() as playwright:
            launch_options: dict[str, Any] = {"headless": True}
            if browser_channel:
                launch_options["channel"] = browser_channel
            browser = await playwright.chromium.launch(**launch_options)
            try:
                for capture_config in captures:
                    if capture_config["kind"] == "recording":
                        await capture_recording(
                            browser, capture_config, base_url, output_dir
                        )
                    else:
                        await capture_screenshot(
                            browser, capture_config, base_url, output_dir
                        )
            finally:
                await browser.close()
    except PlaywrightError as exc:
        raise RuntimeError(str(exc)) from exc


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        asyncio.run(capture(config))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
