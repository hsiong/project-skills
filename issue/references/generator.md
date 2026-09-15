# Issue Generator

Draft and optionally submit English GitHub issues based on Git-tracked changes.

## Grouping Rules

- **Non-source files**: Separate each distinct file path into an independent issue.
- **Source files (Java / Python)**: Group by a single, granular business unit (e.g., one table CRUD flow, or one external API integration across controller/service/DTO).
- **Split signals**: Split when change descriptions contain conjunctions (`and`, `和`, `及`, `/`) or span multiple business modules. When uncertain, prefer smaller issues.
- **Priority**: Process candidate groups in descending order of diff size (`git diff --numstat`).

## Workflow

1. **Retrieve Diffs**:
   - Inspect changes within the user-specified scope (commit, branch, PR, or path). If unspecified, inspect current workspace diffs.
   - Halt if no diff exists.

2. **Deduplication**:
   - Query existing repository issues using `gh issue list`, GitHub API, or web search with candidate keywords (module name, interface, error message).
   - If a duplicate exists, do not draft a new issue; record the existing issue URL, similarities, and differences.

3. **Template Discovery & System Detection**:
   - Check `.github/ISSUE_TEMPLATE/` for issue templates (`.md` or `.yml`).
   - If a template exists, strictly format the draft according to it. For `.yml` form templates, translate form fields (`label`, checkboxes, textareas, dropdowns) into Markdown sections (`### <Label>`).
   - For environment or version fields (OS, Python version, package versions, hardware/device info), execute actual shell commands (e.g., `cat /etc/os-release`, `python3 --version`, `nvidia-smi`) to collect real system data. Never fabricate or hardcode placeholder values.
   - Fallback structure (only when no repository template exists):
     `# Summary`, `# Steps to Reproduce`, `# Expected Behavior`, `# Actual Behavior`, `# Impact`.

4. **Draft Generation**:
   - Clear existing files in `docs/issue/`.
   - Write English Markdown drafts to `docs/issue/<type>-<short-kebab-title>.md` (e.g., `bug-fix-auth-token-refresh.md`). Append `-2`, `-3` on naming collisions.
   - Title prefixes: `Bug:`, `Feature:`, `Refactor:`, `Docs:`, `Chore:`, `Test:`.
   - Issue drafts are strictly local output files and must not be staged or committed to Git.

5. **Submit Issues (Conditional)**:
   - Only when explicitly instructed to submit, invoke `bash scripts/submit_issues.sh [owner/repo] [issue_dir]`.
   - Halt with an informative message if GitHub Token or remote repository is missing.

## Output Requirements

- List generated draft file paths, issue titles, and corresponding change ranges.
- For skipped duplicates, output existing issue links, similarities, and differences.
- If submitted, output final issue URLs, titles, and change ranges.
