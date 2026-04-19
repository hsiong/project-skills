#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib import error
from urllib import parse
from urllib import request


def print_log(stage: str, **kwargs: object) -> None:
	timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
	if kwargs:
		detail_text = ", ".join(f"{key}={json.dumps(value, ensure_ascii=False, default=str)}" for key, value in kwargs.items())
		print(f"[{timestamp}] [{stage}] {detail_text}", flush=True)
		return
	print(f"[{timestamp}] [{stage}]", flush=True)


def build_chat_url(base_url: str, api_path: str) -> str:
	return parse.urljoin(base_url.rstrip("/") + "/", api_path.lstrip("/"))


class OllamaChatClient:
	def __init__(self, base_url: str, api_path: str, model: str, timeout: float) -> None:
		self.base_url = base_url
		self.api_path = api_path
		self.model = model
		self.timeout = timeout
		self.chat_url = build_chat_url(base_url, api_path)

	def chat(self, system_prompt: str, user_prompt: str, chunk_size: int, max_predict: int) -> str:
		payload = {
			"model": self.model,
			"stream": False,
			"messages": [
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			"options": {
				"num_ctx": chunk_size,
				"num_predict": max_predict,
			},
		}
		body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		req = request.Request(
			self.chat_url,
			data=body,
			headers={"Content-Type": "application/json", "Accept": "application/json"},
			method="POST", )
		print_log("ollama.request.start", model=self.model, url=self.chat_url, chunk_size=chunk_size, max_predict=max_predict)
		try:
			with request.urlopen(req, timeout=self.timeout) as response:
				raw_text = response.read().decode("utf-8", errors="replace")
		except error.HTTPError as exc:
			detail = exc.read().decode("utf-8", errors="replace")
			raise RuntimeError(f"ollama request failed: {exc.code} {detail}") from exc
		except error.URLError as exc:
			raise RuntimeError(f"ollama request failed: {exc}") from exc
		try:
			payload_obj = json.loads(raw_text)
		except json.JSONDecodeError as exc:
			raise RuntimeError(f"ollama response is not json: {raw_text[:500]}") from exc
		if isinstance(payload_obj, dict):
			message = payload_obj.get("message")
			if isinstance(message, dict):
				content = message.get("content")
				if isinstance(content, str) and content.strip():
					print_log("ollama.request.done", model=self.model, content_length=len(content))
					return content.strip()
			response_text = payload_obj.get("response")
			if isinstance(response_text, str) and response_text.strip():
				print_log("ollama.request.done", model=self.model, content_length=len(response_text))
				return response_text.strip()
		raise RuntimeError(f"ollama response missing content: {raw_text[:500]}")


def build_analysis_prompt(result_text: str) -> tuple[str, str]:
	system_prompt = (
		"你是一个专门拆解小红书高互动内容的中文策略分析师。"
		"你要基于用户给出的 RESULT.md 样本，归类这些内容，解释每一类为什么容易拿到评论、收藏、点赞和转发。"
		"分析要具体、像操盘手复盘，不要空话。"
		"不要编造样本里没有的事实；拿不准时请明确写“基于样本推断”。"
	)
	user_prompt = (
		"请基于下面的 RESULT.md 原文，输出一份可直接拿来抄作业的爆款拆解报告。\n\n"
		"输出要求：\n"
		"1. 用中文 markdown 输出。\n"
		"2. 先写“总体结论”，总结这些内容的共同高互动机制。\n"
		"3. 再做内容归类，分成 3 到 6 类，每类必须包含以下小节：\n"
		"   - 类别定义\n"
		"   - 代表样本（列出 Item 编号）\n"
		"   - 这类为什么互动高\n"
		"   - 用户为什么愿意评论\n"
		"   - 用户为什么愿意收藏/转发\n"
		"   - 标题怎么写更容易起量\n"
		"   - 正文怎么写更容易让人代入\n"
		"   - 图片/视频怎么配更像高互动内容\n"
		"   - 评论区应该怎么引导\n"
		"   - 我可以直接模仿的 3 条选题模板\n"
		"   - 不要硬抄的点\n"
		"4. 结尾单独输出“优先复制建议”，告诉我最值得优先复制的 3 类内容以及原因。\n"
		"5. 你的判断要尽量结合样本里已经出现的高频因素，比如求推荐、纠结、预算、避坑、自然感、医生口碑、面诊经历、对线、争议感、婚期/时间节点、术前焦虑、效果不确定性、真实感画面。\n"
		"6. 目标是让我后续能直接照着改标题、改正文、改评论引导、改配图思路。\n\n"
		"RESULT.md 原文如下：\n\n"
		f"{result_text}"
	)
	return system_prompt, user_prompt


def run_analysis(result_path: Path,
	             analysis_path: Path,
	             base_url: str,
	             api_path: str,
	             model: str,
	             timeout: float,
	             chunk_size: int,
	             max_predict: int) -> Path:
	if not result_path.exists():
		raise FileNotFoundError(f"RESULT.md not found: {result_path}")
	result_text = result_path.read_text(encoding="utf-8").strip()
	if not result_text:
		raise RuntimeError(f"RESULT.md is empty: {result_path}")
	system_prompt, user_prompt = build_analysis_prompt(result_text)
	client = OllamaChatClient(base_url=base_url, api_path=api_path, model=model, timeout=timeout)
	print_log("analysis.start", result_path=result_path, analysis_path=analysis_path, model=model)
	analysis_text = client.chat(system_prompt, user_prompt, chunk_size, max_predict)
	analysis_path.write_text(analysis_text + "\n", encoding="utf-8")
	print_log("analysis.done", analysis_path=analysis_path, content_length=len(analysis_text))
	return analysis_path


def main() -> int:
	parser = argparse.ArgumentParser(description="Analyze RESULT.md with Ollama qwen3.5:27b and write ANALYSIS.md.")
	parser.add_argument("--out-dir", default="", help="Directory containing RESULT.md")
	parser.add_argument("--result-path", default="", help="Direct path to RESULT.md")
	parser.add_argument("--analysis-path", default="", help="Direct path to ANALYSIS.md")
	parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434", help="Ollama base URL")
	parser.add_argument("--ollama-api-path", default="/api/chat", help="Ollama chat API path")
	parser.add_argument("--ollama-model", default="qwen3.5:27b", help="Ollama model name")
	parser.add_argument("--ollama-timeout", type=float, default=1200.0, help="Request timeout in seconds")
	parser.add_argument("--chunk-size", type=int, default=32000, help="Context window passed to Ollama")
	parser.add_argument("--max-predict", type=int, default=9000, help="Max generated tokens")
	args = parser.parse_args()

	output_dir = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent / "tmp" / "main_test_output"
	result_path = Path(args.result_path) if args.result_path else output_dir / "RESULT.md"
	analysis_path = Path(args.analysis_path) if args.analysis_path else output_dir / "ANALYSIS.md"
	run_analysis(
		result_path=result_path,
		analysis_path=analysis_path,
		base_url=args.ollama_base_url,
		api_path=args.ollama_api_path,
		model=args.ollama_model,
		timeout=args.ollama_timeout,
		chunk_size=args.chunk_size,
		max_predict=args.max_predict, )
	print(str(analysis_path))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
