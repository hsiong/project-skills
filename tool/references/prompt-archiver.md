# Prompt Recording & Archiving

## Core Rules

- **Incremental Date Storage**: User-input prompts are saved incrementally to `docs/prompt.md` by date (new entries at the very top; skip duplicates).
- **Git Protection**: Do not commit this prompt file to Git (ensure `docs/prompt.md` and `docs/prompt.old.md` are added to `.gitignore`).
- **Context & Token Conservation**: Strictly forbid reading (`view_file`) or loading `docs/prompt.md` into context to save tokens; always execute Python or shell script to prepend new entries silently directly to disk.

## Workflow

### 1. Record User Prompt Directly to Disk

Whenever a user input is received that should be archived/recorded into the project, invoke `record_prompt.py` silently via shell without reading `docs/prompt.md` into context:

```bash
python3 /absolute/path/to/tool/scripts/record_prompt.py \
  --project-dir /path/to/project << 'EOF'
<raw user prompt content>
EOF
```

- The script automatically checks `.gitignore` and appends `docs/prompt.md` if not already ignored.
- The script checks if the prompt is already present; if duplicate, it skips without modifying disk.
- New entries are prepended immediately beneath the current date heading (`# YYYY-MM-DD`) at the top of the file.

### 2. Archive Older Prompts (2 Days Ago)

Prompts on or before 2 days ago (`today - 2 days`) can be archived into `docs/prompt.old.md` automatically once per day per project or on demand:

```bash
python3 \
  /absolute/path/to/tool/scripts/archive_prompt.py \
  --project-dir /path/to/project \
  --daily
```
