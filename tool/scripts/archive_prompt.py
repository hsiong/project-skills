from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class DatedSection:
	"""Represents a markdown section associated with a parsed date."""
	header_line: str
	date: datetime.date
	lines: List[str]


def parse_date_from_text(text: str, ref_date: datetime.date) -> Optional[datetime.date]:
	"""
	Extract a date from heading text or filename.
	Supports formats:
	- YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, YYYY年MM月DD日
	- YYYYMMDD
	- MM-DD, MM/DD, MM月DD日
	- MMDD (e.g. 0908)
	"""
	# Match YYYY-MM-DD or variations with separators
	match_full = re.search(r"\b(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?\b", text)
	if match_full:
		year, month, day = int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3))
		try:
			return datetime.date(year, month, day)
		except ValueError:
			pass

	# Match 8-digit compact date: 20260916
	match_compact_8 = re.search(r"\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b", text)
	if match_compact_8:
		year, month, day = int(match_compact_8.group(1)), int(match_compact_8.group(2)), int(match_compact_8.group(3))
		try:
			return datetime.date(year, month, day)
		except ValueError:
			pass

	# Match MM-DD or MM/DD or MM月DD日
	match_month_day = re.search(r"\b(0?[1-9]|1[0-2])[-/.月](0?[1-9]|[12]\d|3[01])日?\b", text)
	if match_month_day:
		month, day = int(match_month_day.group(1)), int(match_month_day.group(2))
		# Infer year: if month/day is ahead of reference date, attribute to previous year
		year = ref_date.year
		if (month, day) > (ref_date.month, ref_date.day):
			year -= 1
		try:
			return datetime.date(year, month, day)
		except ValueError:
			pass

	# Match 4-digit MMDD (e.g., 0908)
	match_compact_4 = re.search(r"\b(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b", text)
	if match_compact_4:
		month, day = int(match_compact_4.group(1)), int(match_compact_4.group(2))
		year = ref_date.year
		if (month, day) > (ref_date.month, ref_date.day):
			year -= 1
		try:
			return datetime.date(year, month, day)
		except ValueError:
			pass

	return None


def parse_markdown_file(file_path: Path, ref_date: datetime.date) -> Tuple[List[str], List[DatedSection]]:
	"""
	Parse a markdown file into prologue lines and dated sections.
	Only headings containing recognizable dates delimit new dated sections.
	Subheadings without dates belong to the current dated section.
	"""
	lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)

	prologue: List[str] = []
	sections: List[DatedSection] = []
	current_section: Optional[DatedSection] = None

	heading_regex = re.compile(r"^(#{1,6})\s+(.*)$")

	for line in lines:
		heading_match = heading_regex.match(line.strip())
		if heading_match:
			heading_title = heading_match.group(2)
			date_found = parse_date_from_text(heading_title, ref_date)
			if date_found is not None:
				# Finalize previous section if present
				if current_section is not None:
					sections.append(current_section)
				current_section = DatedSection(header_line=line, date=date_found, lines=[line])
				continue

		if current_section is not None:
			current_section.lines.append(line)
		else:
			prologue.append(line)

	if current_section is not None:
		sections.append(current_section)

	return prologue, sections


def get_state_file_path(project_dir: Path) -> Path:
	"""
	Return the state tracking file path for daily execution checks.
	Uses .git/prompt_archive_last_run if inside a git repository,
	otherwise falls back to ~/.cache/prompt_archive/<project_hash>.last_run.
	"""
	git_dir = project_dir / ".git"
	if git_dir.is_dir():
		return git_dir / "prompt_archive_last_run"

	cache_dir = Path.home() / ".cache" / "prompt_archive"
	cache_dir.mkdir(parents=True, exist_ok=True)
	project_hash = hashlib.md5(str(project_dir.resolve()).encode("utf-8")).hexdigest()
	return cache_dir / f"{project_hash}.last_run"


def record_last_run(project_dir: Path, run_date: datetime.date) -> None:
	"""Record the successful run date in the state tracking file."""
	try:
		state_file = get_state_file_path(project_dir)
		state_file.parent.mkdir(parents=True, exist_ok=True)
		state_file.write_text(str(run_date), encoding="utf-8")
	except OSError:
		pass


def check_already_run_today(project_dir: Path, ref_date: datetime.date) -> bool:
	"""Check whether prompt archiving has already executed today for the given project."""
	state_file = get_state_file_path(project_dir)
	if state_file.exists():
		try:
			last_run_str = state_file.read_text(encoding="utf-8").strip()
			return last_run_str == str(ref_date)
		except OSError:
			pass
	return False


def archive_single_file(
	source_path: Path,
	target_path: Path,
	cutoff_date: datetime.date,
	ref_date: datetime.date,
	dry_run: bool = False,
) -> int:
	"""
	Archive dated sections older than or on cutoff_date from source markdown to target markdown.
	"""
	if not source_path.exists():
		print(f"Error: Source file '{source_path}' does not exist.", file=sys.stderr)
		return 1

	prologue, sections = parse_markdown_file(source_path, ref_date)

	if not sections:
		print(f"Warning: No dated sections found in '{source_path}'. Nothing to archive.")
		return 0

	to_keep: List[DatedSection] = []
	to_archive: List[DatedSection] = []

	for sec in sections:
		if sec.date <= cutoff_date:
			to_archive.append(sec)
		else:
			to_keep.append(sec)

	if not to_archive:
		print(f"No prompt sections on or before {cutoff_date} found. Nothing to archive.")
		return 0

	print(f"Found {len(to_archive)} dated section(s) on or before {cutoff_date} to archive:")
	for sec in to_archive:
		title = sec.header_line.strip()
		print(f"  - [{sec.date}] {title} ({len(sec.lines)} lines)")

	if dry_run:
		print(f"\n[Dry Run] Would move {len(to_archive)} section(s) to '{target_path}'.")
		return 0

	# Ensure target directory exists
	target_path.parent.mkdir(parents=True, exist_ok=True)

	# Format archive content
	archive_content = ""
	for sec in to_archive:
		archive_content += "".join(sec.lines)
		if not archive_content.endswith("\n"):
			archive_content += "\n"
		if not archive_content.endswith("\n\n"):
			archive_content += "\n"

	# Append or create target file
	if target_path.exists():
		existing_target_text = target_path.read_text(encoding="utf-8")
		if existing_target_text and not existing_target_text.endswith("\n\n"):
			if existing_target_text.endswith("\n"):
				existing_target_text += "\n"
			else:
				existing_target_text += "\n\n"
		target_path.write_text(existing_target_text + archive_content, encoding="utf-8")
	else:
		default_header = "# 提示词归档 (Prompt Archive)\n\n"
		target_path.write_text(default_header + archive_content, encoding="utf-8")

	# Update source file with kept sections
	new_source_content = "".join(prologue)
	if new_source_content and not new_source_content.endswith("\n\n"):
		if new_source_content.endswith("\n"):
			new_source_content += "\n"
		else:
			new_source_content += "\n\n"

	for sec in to_keep:
		new_source_content += "".join(sec.lines)
		if not new_source_content.endswith("\n"):
			new_source_content += "\n"
		if not new_source_content.endswith("\n\n"):
			new_source_content += "\n"

	# Trim trailing blank lines to a single newline
	new_source_content = new_source_content.rstrip() + "\n"
	source_path.write_text(new_source_content, encoding="utf-8")

	print(f"Successfully archived {len(to_archive)} section(s) to '{target_path}'.")
	print(f"Remaining active sections in '{source_path}': {len(to_keep)}.")
	return 0


def archive_directory(
	source_dir: Path,
	target_path: Path,
	cutoff_date: datetime.date,
	ref_date: datetime.date,
	dry_run: bool = False,
) -> int:
	"""
	Archive files older than or on cutoff_date from source directory to target markdown file.
	"""
	if not source_dir.exists() or not source_dir.is_dir():
		print(f"Error: Source directory '{source_dir}' does not exist or is not a directory.", file=sys.stderr)
		return 1

	eligible_files: List[Tuple[Path, datetime.date]] = []

	for child in sorted(source_dir.iterdir()):
		if not child.is_file():
			continue

		file_date = parse_date_from_text(child.stem, ref_date)
		if file_date is None:
			mtime = os.path.getmtime(child)
			file_date = datetime.datetime.fromtimestamp(mtime).date()

		if file_date <= cutoff_date:
			eligible_files.append((child, file_date))

	if not eligible_files:
		print(f"No prompt files on or before {cutoff_date} found in '{source_dir}'. Nothing to archive.")
		return 0

	print(f"Found {len(eligible_files)} file(s) on or before {cutoff_date} to archive:")
	for file_path, file_date in eligible_files:
		print(f"  - [{file_date}] {file_path.name}")

	if dry_run:
		print(f"\n[Dry Run] Would move {len(eligible_files)} file(s) to '{target_path}'.")
		return 0

	target_path.parent.mkdir(parents=True, exist_ok=True)

	archive_content = ""
	for file_path, file_date in eligible_files:
		content = file_path.read_text(encoding="utf-8").strip()
		archive_content += f"## {file_path.name} ({file_date})\n\n{content}\n\n"

	if target_path.exists():
		existing_target_text = target_path.read_text(encoding="utf-8")
		if existing_target_text and not existing_target_text.endswith("\n\n"):
			if existing_target_text.endswith("\n"):
				existing_target_text += "\n"
			else:
				existing_target_text += "\n\n"
		target_path.write_text(existing_target_text + archive_content, encoding="utf-8")
	else:
		default_header = "# 提示词归档 (Prompt Archive)\n\n"
		target_path.write_text(default_header + archive_content, encoding="utf-8")

	for file_path, _ in eligible_files:
		file_path.unlink()

	print(f"Successfully archived {len(eligible_files)} file(s) to '{target_path}'.")
	return 0


def auto_detect_source_and_target(project_dir: Path) -> Tuple[Optional[Path], Path]:
	"""
	Auto-detect prompt source and archive destination paths within the project directory.
	Checks:
	1. <project_dir>/docs/prompt.md
	2. <project_dir>/docs/prompt (file or directory)
	3. <project_dir>/prompt.md
	"""
	candidates = [
		project_dir / "docs" / "prompt.md",
		project_dir / "docs" / "prompt",
		project_dir / "prompt.md",
	]

	for candidate in candidates:
		if candidate.exists():
			if candidate.is_dir():
				target = project_dir / "docs" / "prompt.old.md"
				return candidate, target
			if candidate.parent.name == "docs":
				target = project_dir / "docs" / "prompt.old.md"
			else:
				target = project_dir / "prompt.old.md"
			return candidate, target

	return None, project_dir / "docs" / "prompt.old.md"


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Archive prompts older than N days (default 2 days) from docs/prompt to prompt.old.md."
	)
	parser.add_argument(
		"source",
		nargs="?",
		default=None,
		help="Source file or directory (default: auto-detected docs/prompt.md or docs/prompt).",
	)
	parser.add_argument(
		"-t",
		"--target",
		default=None,
		help="Target archive markdown file (default: docs/prompt.old.md).",
	)
	parser.add_argument(
		"-d",
		"--days",
		type=int,
		default=2,
		help="Number of days threshold. Items older than or equal to this many days are archived (default: 2).",
	)
	parser.add_argument(
		"-p",
		"--project-dir",
		default=".",
		help="Project root directory (default: current working directory).",
	)
	parser.add_argument(
		"--date",
		default=None,
		help="Base reference date in YYYY-MM-DD format (default: today's date).",
	)
	parser.add_argument(
		"--daily",
		action="store_true",
		default=False,
		help="Enable daily check: exit early if already executed today for this project.",
	)
	parser.add_argument(
		"-f",
		"--force",
		action="store_true",
		help="Force execution even if already run today.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview the changes without writing to disk.",
	)

	args = parser.parse_args()

	project_dir = Path(args.project_dir).resolve()

	if args.date:
		ref_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
	else:
		ref_date = datetime.date.today()

	# Daily check: if --daily is passed and not forcing, check if already run today
	if args.daily and not args.force:
		if check_already_run_today(project_dir, ref_date):
			print(f"Prompt archive already executed today ({ref_date}) for '{project_dir}'. Skipping.")
			return 0

	cutoff_date = ref_date - datetime.timedelta(days=args.days)
	print(f"Reference date: {ref_date}, Threshold: {args.days} days, Cutoff date: {cutoff_date}")

	# Resolve source and target
	if args.source:
		source_path = Path(args.source)
		if not source_path.is_absolute():
			source_path = (project_dir / source_path).resolve()
	else:
		detected_source, detected_target = auto_detect_source_and_target(project_dir)
		if detected_source is None:
			print(
				f"Notice: No prompt file or directory (docs/prompt.md, docs/prompt, prompt.md) found in '{project_dir}'. "
				"Skipping archive.",
			)
			return 0
		source_path = detected_source

	if args.target:
		target_path = Path(args.target)
		if not target_path.is_absolute():
			target_path = (project_dir / target_path).resolve()
	else:
		if source_path.parent.name == "docs":
			target_path = source_path.parent / "prompt.old.md"
		else:
			target_path = project_dir / "docs" / "prompt.old.md"

	print(f"Source: {source_path}")
	print(f"Target: {target_path}")

	if source_path.is_dir():
		ret = archive_directory(
			source_dir=source_path,
			target_path=target_path,
			cutoff_date=cutoff_date,
			ref_date=ref_date,
			dry_run=args.dry_run,
		)
	else:
		ret = archive_single_file(
			source_path=source_path,
			target_path=target_path,
			cutoff_date=cutoff_date,
			ref_date=ref_date,
			dry_run=args.dry_run,
		)

	if ret == 0 and not args.dry_run:
		record_last_run(project_dir, ref_date)

	return ret


if __name__ == "__main__":
	sys.exit(main())
