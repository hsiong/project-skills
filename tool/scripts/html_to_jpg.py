from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


def _find_chrome_executable() -> str:
	"""Locate an installed Chrome, Chromium, or Edge executable."""
	env_custom_path = os.environ.get("CHROME_PATH")
	if env_custom_path and os.path.exists(env_custom_path):
		return env_custom_path

	candidate_paths = [
		"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
		"/Applications/Chromium.app/Contents/MacOS/Chromium",
		"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
		shutil.which("google-chrome"),
		shutil.which("chromium"),
		shutil.which("chrome"),
		shutil.which("msedge"),
	]

	for candidate_path in candidate_paths:
		if candidate_path and os.path.exists(candidate_path):
			return candidate_path

	raise FileNotFoundError(
		"Could not find a headless browser (Google Chrome / Chromium / Microsoft Edge). "
		"Please install Google Chrome or set CHROME_PATH environment variable."
	)


def _estimate_page_height(html_content: str, default_width: int = 750) -> int:
	"""Estimate a viewport height from common content elements in the HTML."""
	img_count = html_content.count("<img")
	section_count = html_content.count("<section")
	p_count = html_content.count("<p")
	table_count = html_content.count("<table")

	# Reserve room for page framing before adding content-specific height.
	base_height = 2000
	estimated = base_height + (img_count * 800) + (table_count * 250) + (section_count * 80) + (p_count * 40)
	return max(4000, min(estimated, 30000))


def _crop_trailing_whitespace(rgb_img: Image.Image) -> Image.Image:
	"""Trim uniform blank padding from the bottom of a rendered screenshot."""
	width, height = rgb_img.size
	bg_pixel = rgb_img.getpixel((width // 2, height - 1))

	crop_y = height
	step = 6
	for y_position in range(height - 1, 0, -step):
		row_samples = [rgb_img.getpixel((x_position, y_position)) for x_position in range(10, width, 40)]
		if any(pixel != bg_pixel for pixel in row_samples):
			crop_y = min(height, y_position + 24)
			break

	if crop_y < height:
		return rgb_img.crop((0, 0, width, crop_y))
	return rgb_img


def convert_html_to_jpg(
	html_path: str | Path,
	output_jpg_path: str | Path | None = None,
	width: int = 750,
	quality: int = 95,
) -> str:
	"""Render a local HTML file and return the saved JPG path."""
	source_html = Path(html_path).expanduser().resolve()
	if not source_html.exists():
		fallback = source_html.parent / "jiarui" / source_html.name
		if fallback.exists():
			source_html = fallback
		else:
			raise FileNotFoundError(f"HTML file does not exist: {html_path}")

	base_dir = source_html.parent
	if output_jpg_path is None:
		target_jpg_file = base_dir / f"{source_html.stem}.jpg"
	else:
		target_jpg_file = Path(output_jpg_path).expanduser().resolve()

	target_jpg_file.parent.mkdir(parents=True, exist_ok=True)

	chrome_bin = _find_chrome_executable()
	html_content = source_html.read_text(encoding="utf-8", errors="ignore")
	viewport_height = _estimate_page_height(html_content, default_width=width)

	with tempfile.TemporaryDirectory() as tmp_dir:
		tmp_png_path = Path(tmp_dir) / f"{source_html.stem}_render.png"
		file_url = source_html.as_uri()
		cmd = [
			chrome_bin,
			"--headless=new",
			"--disable-gpu",
			"--hide-scrollbars",
			"--default-background-color=ffffff",
			f"--screenshot={tmp_png_path}",
			f"--window-size={width},{viewport_height}",
			file_url,
		]

		try:
			subprocess.run(
				cmd,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				check=True,
				timeout=60,
			)
		except subprocess.CalledProcessError as exc:
			raise RuntimeError(f"Headless Chrome screenshot failed: {exc}") from exc

		if not tmp_png_path.exists():
			raise FileNotFoundError(f"Chrome did not generate expected screenshot at: {tmp_png_path}")

		# JPEG has no alpha channel, so composite transparent pixels onto white.
		with Image.open(tmp_png_path) as raw_img:
			if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
				background = Image.new("RGB", raw_img.size, (255, 255, 255))
				alpha_mask = raw_img.split()[-1] if raw_img.mode == "RGBA" else None
				background.paste(raw_img, mask=alpha_mask)
				rgb_img = background
			else:
				rgb_img = raw_img.convert("RGB")

			final_img = _crop_trailing_whitespace(rgb_img)
			final_img.save(
				str(target_jpg_file),
				format="JPEG",
				quality=quality,
				optimize=True,
				progressive=True,
			)

	print(f"Successfully converted HTML to JPG: {target_jpg_file}")
	return str(target_jpg_file)


html_to_jpg = convert_html_to_jpg


if __name__ == "__main__":
	if len(sys.argv) < 2 or len(sys.argv) > 5:
		print("Usage: python3 html_to_jpg.py INPUT_HTML [OUTPUT_JPG] [WIDTH] [QUALITY]")
		raise SystemExit(2)

	input_html_path = sys.argv[1]
	output_path = sys.argv[2] if len(sys.argv) >= 3 else None
	output_width = int(sys.argv[3]) if len(sys.argv) >= 4 else 750
	output_quality = int(sys.argv[4]) if len(sys.argv) >= 5 else 95
	convert_html_to_jpg(input_html_path, output_path, output_width, output_quality)
