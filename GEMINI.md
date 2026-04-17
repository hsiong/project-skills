# Project: Codex Skills

This repository is a collection of "skills" for the Gemini CLI and Codex. Each skill is a self-contained directory that provides specialized instructions, scripts, and references to handle specific tasks.

## Workspace Overview

The project is structured as a collection of specialized agents, each defined by a `SKILL.md` file. The skills are designed to be used by LLMs to perform complex tasks, often involving external tools and scripts.

### Key Skills

- **`chrome-extractor-rn-v2`**: A powerful tool for extracting structured content from web pages (especially social media like Rednote). It uses a local GUI Chrome instance, automates comment expansion, exports cleaned HTML, and uses Ollama-compatible models for analysis.
- **`commit_chinese` / `commit_english`**: Git commit helpers that enforce specific grouping rules and message formats. They include safety checks like preventing commits with `todo` markers.
- **`github-issue-generator`**: Assists in creating high-quality GitHub issues by checking for duplicates and following repository templates.
- **Code Style Skills**: `java-code-style`, `python-code-style`, and `java-feign-integration` provide project-specific coding conventions and patterns.
- **`skill-creator`**: A meta-skill for building new skills.

## Core Technologies

- **Languages**: Python (for automation scripts), Markdown (for skill definitions and documentation).
- **Automation**: `wmctrl`, `xlib`, `ctypes` (for GUI interaction on Linux), `subprocess`.
- **LLM Integration**: Ollama-compatible APIs for HTML analysis and media recognition.
- **Source Control**: Git.

## Development Conventions

- **Skill Structure**: Each skill must have a `SKILL.md` with YAML front matter (`name`, `description`). Optional directories include `scripts/`, `references/`, `assets/`, and `agents/`.
- **Prompt History**: Original prompts are stored in `.prompt/{skill_name}.md`, and revisions are versioned as `{skill_name}_{hhmmss}.md`.
- **Execution**: Skills often delegate complex work to Python scripts in their `scripts/` directory.

## Getting Started

### Creating a New Skill
Use the `skill-creator` skill or manually create a folder with a `SKILL.md` file following the template in `Readme.md`.

### Running the Extractor (v2)
Requires a Linux environment with X11/Xephyr.
```bash
python3 extractor-rn-vision-v2/scripts/extractor_html_x11.py <url>
```
Common options:
- `--xephyr-session <name>`: Reuse a persistent Xephyr session.
- `--prepare-login`: Open Chrome for manual login before extraction.
- `--ollama-model <model>`: Specify the parsing model.

## Rules & Guardrails

- **No Secrets**: Never commit or log API keys or sensitive credentials.
- **Grouping**: Non-programming files with different names or paths must be committed separately (as per `commit_chinese`/`commit_english` rules).
- **TODO Check**: Commits are blocked if the changed code contains `todo` unless explicitly allowed.
