from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path
from typing import Optional


def ensure_gitignored(project_dir: Path) -> None:
	"""
	Ensure docs/prompt.md and docs/prompt.old.md are ignored in .gitignore
	so they are never accidentally committed to Git.
	"""
	gitignore_path = project_dir / ".gitignore"
	patterns_to_add = ["docs/prompt.md", "docs/prompt.old.md"]

	if gitignore_path.exists():
		content = gitignore_path.read_text(encoding="utf-8")
		lines = content.splitlines()
		missing = [p for p in patterns_to_add if p not in lines]
		if missing:
			new_content = content
			if new_content and not new_content.endswith("\n"):
				new_content += "\n"
			new_content += "\n".join(missing) + "\n"
			gitignore_path.write_text(new_content, encoding="utf-8")
	else:
		gitignore_path.write_text("\n".join(patterns_to_add) + "\n", encoding="utf-8")


def normalize_text(text: str) -> str:
	"""Normalize whitespace for duplicate detection."""
	return " ".join(text.strip().split())


def is_duplicate(prompt_text: str, existing_content: str) -> bool:
	"""Check whether the given prompt already exists in the file."""
	normalized_prompt = normalize_text(prompt_text)
	if not normalized_prompt:
		return True

	# Exact substring check first
	if prompt_text.strip() in existing_content:
		return True

	# Normalized line check
	normalized_existing = normalize_text(existing_content)
	return normalized_prompt in normalized_existing


def prepend_prompt(
	file_path: Path,
	prompt_text: str,
	ref_date: datetime.date,
) -> bool:
	"""
	Prepend the prompt under the date heading at the very top of the markdown file.
	Skips if prompt is duplicate.
	"""
	prompt_text = prompt_text.strip()
	if not prompt_text:
		print("Warning: Empty prompt provided. Skipping.", file=sys.stderr)
		return False

	existing_content = ""
	if file_path.exists():
		existing_content = file_path.read_text(encoding="utf-8")

	if is_duplicate(prompt_text, existing_content):
		print(f"Prompt already exists in '{file_path}'. Skipped duplicate.")
		return False

	date_heading = f"# {ref_date.isoformat()}"
	new_entry = f"{prompt_text}\n"

	# Check if file already begins with today's date heading
	heading_pattern = re.compile(rf"^#+\s+{re.escape(ref_date.isoformat())}\b", re.MULTILINE)
	match = heading_pattern.search(existing_content)

	if match and match.start() == 0:
		# Today's heading is already at the very top of the file
		# Insert the new prompt right under the heading
		header_end = existing_content.find("\n")
		if header_end == -1:
			header_end = len(existing_content)
			updated_content = f"{existing_content}\n\n{new_entry}"
		else:
			after_header = existing_content[header_end + 1:].lstrip("\n")
			updated_content = f"{existing_content[:header_end + 1]}\n{new_entry}\n{after_header}"
	else:
		# Today's heading is not at the top; prepend the new date section
		if existing_content.strip():
			updated_content = f"{date_heading}\n\n{new_entry}\n{existing_content.lstrip()}"
		else:
			updated_content = f"{date_heading}\n\n{new_entry}"

	file_path.parent.mkdir(parents=True, exist_ok=True)
	file_path.write_text(updated_content.rstrip() + "\n", encoding="utf-8")
	print(f"Successfully recorded prompt to '{file_path}' under [{ref_date}].")
	return True


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Silently prepend user-input prompts to docs/prompt.md by date directly on disk."
	)
	parser.add_argument(
		"prompt",
		nargs="?",
		default=None,
		help="The user prompt text to record. If omitted, reads from stdin.",
	)
	parser.add_argument(
		"-p",
		"--project-dir",
		default=".",
		help="Project root directory (default: current working directory).",
	)
	parser.add_argument(
		"--file",
		"-f",
		default=None,
		help="Path to target prompt file (default: <project_dir>/docs/prompt.md).",
	)
	parser.add_argument(
		"--date",
		default=None,
		help="Date override in YYYY-MM-DD format (default: today's date).",
	)

	args = parser.parse_args()

	project_dir = Path(args.project_dir).resolve()

	# Read prompt text from arg or stdin
	prompt_text: Optional[str] = args.prompt
	if prompt_text is None:
		if not sys.stdin.isatty():
			prompt_text = sys.stdin.read()
		else:
			print("Error: No prompt provided via argument or standard input.", file=sys.stderr)
			return 1

	if args.date:
		try:
			ref_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
		except ValueError:
			print(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.", file=sys.stderr)
			return 1
	else:
		ref_date = datetime.date.today()

	# Ensure docs/prompt.md is in .gitignore
	ensure_gitignored(project_dir)

	# Determine target file path
	if args.file:
		target_file = Path(args.file)
		if not target_file.is_absolute():
			target_file = (project_dir / target_file).resolve()
	else:
		target_file = project_dir / "docs" / "prompt.md"

	prepend_prompt(target_file, prompt_text, ref_date)
	return 0


if __name__ == "__main__":
	sys.exit(main())
