
from extractor_html_x11 import *
# CDP
import itertools
import websocket

CDP_DEBUG_PORT = 7005
EXPAND_REPLY_TEXT_RE = re.compile(r"^展开\s*\d+\s*条回复$")

_cdp_message_id = itertools.count(1)


def cdp_list_targets(debug_port: int = CDP_DEBUG_PORT) -> list[dict]:
	with request.urlopen(f"http://127.0.0.1:{debug_port}/json", timeout=3) as response:
		return json.loads(response.read().decode("utf-8"))


def cdp_get_target_ws(
		debug_port: int = CDP_DEBUG_PORT,
		url_hint: str | None = None,
		title_hint: str | None = None,
) -> str:
	targets = cdp_list_targets(debug_port)
	page_targets = [target for target in targets if target.get("type") == "page"]
	if url_hint:
		for target in page_targets:
			if url_hint in (target.get("url") or ""):
				return target["webSocketDebuggerUrl"]
	if title_hint:
		lowered = title_hint.lower()
		for target in page_targets:
			if lowered in (target.get("title") or "").lower():
				return target["webSocketDebuggerUrl"]
	if not page_targets:
		raise RuntimeError("no page target found")
	return page_targets[0]["webSocketDebuggerUrl"]


def cdp_send(ws: websocket.WebSocket, method: str, params: dict | None = None) -> dict:
	message_id = next(_cdp_message_id)
	ws.send(json.dumps({
		"id": message_id,
		"method": method,
		"params": params or {},
	}, ensure_ascii=False))
	while True:
		payload = json.loads(ws.recv())
		if payload.get("id") != message_id:
			continue
		if "error" in payload:
			raise RuntimeError(f"CDP error: {payload['error']}")
		return payload


def cdp_eval(ws: websocket.WebSocket, expression: str):
	response = cdp_send(
		ws,
		"Runtime.evaluate",
		{
			"expression": expression,
			"returnByValue": True,
			"awaitPromise": True,
		},
	)
	return response["result"]["result"].get("value")


def build_expand_reply_probe_js(target_x_ratio: float, target_y_ratio: float) -> str:
	return f"""
(() => {{
	const targetWindowX = {target_x_ratio:.8f};
	const targetWindowY = {target_y_ratio:.8f};

	const viewportWidth = Math.max(window.innerWidth, 1);
	const viewportHeight = Math.max(window.innerHeight, 1);

	const candidates = [];
	for (const el of document.querySelectorAll("*")) {{
		const text = ((el.innerText || el.textContent || "") + "").replace(/\\s+/g, " ").trim();
		if (!/^展开\\s*\\d+\\s*条回复$/.test(text)) {{
			continue;
		}}
		const rect = el.getBoundingClientRect();
		if (rect.width <= 0 || rect.height <= 0) {{
			continue;
		}}
		const style = window.getComputedStyle(el);
		if (style.display === "none" || style.visibility === "hidden") {{
			continue;
		}}
		const centerX = rect.left + rect.width / 2;
		const centerY = rect.top + rect.height / 2;
		const xRatio = centerX / viewportWidth;
		const yRatio = centerY / viewportHeight;
		const dx = xRatio - targetWindowX;
		const dy = yRatio - targetWindowY;
		candidates.push({{
			text,
			left: rect.left,
			top: rect.top,
			width: rect.width,
			height: rect.height,
			xRatio,
			yRatio,
			score: Math.abs(dx) + Math.abs(dy),
		}});
	}}

	candidates.sort((a, b) => a.score - b.score);

	return {{
		found: candidates.length > 0,
		best: candidates[0] || null,
		all: candidates.slice(0, 10),
	}};
}})()
""".strip()


def cdp_click_expand_reply_near_target(
		target: ExpandReplyTarget,
		geometry: dict[str, int],
		window_title_hint: str | None = None,
) -> tuple[bool, str]:
	target_x_ratio = target.x / max(geometry["width"], 1)
	target_y_ratio = target.y / max(geometry["height"], 1)

	ws_url = cdp_get_target_ws(
		debug_port=CDP_DEBUG_PORT,
		url_hint="xiaohongshu.com",
		title_hint=window_title_hint,
	)
	ws = websocket.create_connection(ws_url, timeout=5)
	try:
		probe = cdp_eval(ws, build_expand_reply_probe_js(target_x_ratio, target_y_ratio))
		if not isinstance(probe, dict) or not probe.get("found") or not probe.get("best"):
			return False, "not-found"

		best = probe["best"]
		best_text = str(best.get("text", "")).strip()
		if not EXPAND_REPLY_TEXT_RE.fullmatch(best_text):
			return False, f"text-mismatch:{best_text}"

		click_result = cdp_eval(ws, f"""
(() => {{
	const targetText = {json.dumps(best_text, ensure_ascii=False)};
	const matches = Array.from(document.querySelectorAll("*")).filter(el => {{
		const text = ((el.innerText || el.textContent || "") + "").replace(/\\s+/g, " ").trim();
		return text === targetText;
	}});
	if (!matches.length) {{
		return {{ok: false, reason: "missing-before-click"}};
	}}
	matches[0].click();
	return {{ok: true, text: targetText}};
}})()
""".strip())

		if isinstance(click_result, dict) and click_result.get("ok"):
			return True, best_text
		return False, f"click-failed:{click_result}"
	finally:
		ws.close()
###################################### CDP END ########################################
