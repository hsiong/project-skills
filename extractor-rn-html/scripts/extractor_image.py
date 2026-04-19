#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import extractor_html_x11
from extractor_html_x11 import RnOllamaClient
from extractor_html_x11 import build_report
from extractor_html_x11 import log_event
from extractor_html_x11 import read_media_bytes


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".bin"}



def collect_item_manifest_paths(output_dir: Path) -> list[Path]:
    def item_index(path: Path) -> int:
        # path.parent.name like: item_1 / item_2 / item_10
        return int(path.parent.name.removeprefix("item_"))

    return sorted(
        (
            path
            for path in output_dir.glob("item_*/manifest.json")
            if path.parent.name.startswith("item_")
        ),
        key=item_index,
    )


def read_image_base64(image_path: Path, page_url: str) -> str:
    image_bytes = read_media_bytes(str(image_path), page_url)
    return base64.b64encode(image_bytes).decode("ascii")


def analyze_image(client: RnOllamaClient, image_path: Path, page_url: str) -> str:
    image_base64 = read_image_base64(image_path, page_url)
    prompt = (
        "请直接描述这张图片的可见内容，只返回简洁中文，不要 markdown，不要分点，不要补充推测。"
        "如果图片里主要是文字、界面、海报、人物、商品、风景，请按实际看到的内容描述。"
    )
    return client.chat(prompt, chunk_size=8000, images=[image_base64]).strip()


def analyze_manifest(manifest_path: Path, client: RnOllamaClient) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_results: list[dict[str, str]] = []
    page_url = str(manifest.get("url", "")).strip()
    image_paths = manifest.get("图片", [])
    if not isinstance(image_paths, list):
        image_paths = []
    for image_value in image_paths:
        image_path = Path(str(image_value))
        image_record = {"图片": str(image_path)}
        try:
            if not image_path.exists():
                raise FileNotFoundError(f"image not found: {image_path}")
            if image_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                raise RuntimeError(f"unsupported image suffix: {image_path.suffix}")
            image_record["识别结果"] = analyze_image(client, image_path, page_url)
        except Exception as exc:  # noqa: BLE001
            image_record["异常"] = str(exc)
        image_results.append(image_record)
    manifest["图片识别"] = image_results
    manifest.pop("图片识别异常", None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def analyze_output_dir(
    output_dir: Path,
    client: RnOllamaClient,
) -> list[dict[str, object]]:
    manifests: list[dict[str, object]] = []
    for manifest_path in collect_item_manifest_paths(output_dir):
        log_event("image_analysis.manifest.start", manifest_path=manifest_path)
        manifest = analyze_manifest(manifest_path, client)
        log_event(
            "image_analysis.manifest.done",
            manifest_path=manifest_path,
            image_result_count=len(manifest.get("图片识别", [])),
            image_error_count=len([item for item in manifest.get("图片识别", []) if "异常" in item]),
        )
        manifests.append(manifest)
    return manifests


def rebuild_report(output_dir: Path) -> Path:
    manifests = [
        json.loads(manifest_path.read_text(encoding="utf-8"))
        for manifest_path in collect_item_manifest_paths(output_dir)
    ]
    extractor_html_x11.ROOT_DIR = output_dir
    report_path = output_dir / "RESULT.md"
    report_path.write_text(build_report(manifests), encoding="utf-8")
    log_event("image_analysis.report.done", manifest_count=len(manifests), report_path=report_path)
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Use Ollama to analyze item images and write results back to manifest.json.")
    parser.add_argument("--out-dir", default="", help="Extractor output directory containing item_*/manifest.json")
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434", help="Base URL for the Ollama-compatible endpoint")
    parser.add_argument("--ollama-api-path", default="/api/chat", help="API path for the Ollama-compatible chat endpoint")
    parser.add_argument("--ollama-model", default="qwen3-vl:8b", help="Model name for the Ollama-compatible endpoint")
    parser.add_argument("--ollama-timeout", type=float, default=180.0, help="Timeout for each Ollama-compatible request")
    args = parser.parse_args()

    output_dir = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent / "tmp" / "main_test_output"
    client = RnOllamaClient(
        base_url=args.ollama_base_url,
        api_path=args.ollama_api_path,
        model=args.ollama_model,
        timeout=args.ollama_timeout,
    )
    analyze_output_dir(output_dir, client)
    rebuild_report(output_dir)
    print(str(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
