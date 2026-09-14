---
name: git-commit
description: "Handle local Git commits and milestone tagging when users say commit, 提交, milestone, milestone tag, 中文 commit, English commit, or ask to split changes into commits. Do not trigger for code editing, issue-linked push workflows, untracked-file inspection, or push-only requests."
---

# Git Commit

Create focused conventional commits from the repository's Git-known changes, and tag milestone releases when requested.

## Language

- If the user explicitly specifies the commit language in the trigger prompt (e.g., "中文 commit", "English commit"), use that language directly without prompting.
- Otherwise, interact with the user before committing to choose the commit message language:
  1. English (Default / Enter)
  2. Chinese (中文)
  3. Custom input
- Treat an empty reply or Enter as English. When option 3 is chosen, follow the user's custom language or style instructions.
- Keep the commit message entirely in the selected language, apart from the conventional commit type.

## Scope

- Perform commit and milestone tagging operations only. Do not edit code, reformat files, or fix unrelated problems.
- Inspect only tracked changes, staged additions, and staged deletions. Ignore untracked files without reading their contents.
- Read `.gitignore`, but do not access or commit ignored content.
- Exclude `*/application.yml`, `*/application-*.yml`, `*/.fastRequest/*`, `*/.mvn/*`, `*/.idea/*`, `*/.antigravity/*`, `*/.vscode/*`, `*/.git/*`, `config/.env.*` (except `.env.example`), and `*/.DS_Store`.
- Never run `git push` for standard commits; use the issue-specific commit workflow instead when an issue number and remote branch are part of the request.

## Safety Gates

Before staging or committing, inspect the final content of every candidate file.

- If candidate code contains `TODO` in any letter case, stop and report each file and line number.
- If content appears to contain a real secret, credential, private key, cookie, session value, database or cloud credential, personal contact or identity data, financial data, precise location, health or biometric data, private image URL, or non-public internal address or dataset, stop and report only the masked location and data type.
- Explicit placeholders, redacted examples, and fictional test data are allowed.

Do not stage anything until all gates pass. Stage only the approved Git-known pathspecs; never allow a repository-wide add to capture an untracked or excluded file.

## Commit Groups

Use `git diff --numstat` and `git diff --stat` to estimate each group's changed lines.

- For files other than Java and Python source, commit each distinct file path separately.
- Java and Python files may share a commit only when they implement one narrowly defined business change, such as one external API integration or one table's CRUD flow, including its controller, service, client, DTO, test, and documentation.
- Split multiple integrations, multiple tables, different modules, or scopes joined by `/`, `and`, `和`, `及`, `以及`, `并`, or `等`.
- When uncertain, prefer the smaller independent group. If safe separation is impossible, stop and explain why.
- Commit multiple groups from largest to smallest by total additions and deletions.

## Commit Messages

- Use a conventional type such as `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`, `build`, `ci`, or `perf`.
- Keep the title concrete and concise. Do not include file names or sequence numbers.
- When one file contains multiple concrete changes, describe them in the body with hyphen bullets rather than numbered items.

## Milestone Tagging

When the user specifies `milestone`:
- Extract the milestone tag name from the input (e.g., `v1.0.0`, `milestone-1.0`). If no tag name or version is given, ask the user to supply one before creating the tag.
- Apply the tag to the latest commit (`HEAD`) after all pending commits finish, or to the current `HEAD` if no new commits are made.
- Before creating the tag, locate the most recent prior tag with `git describe --tags --abbrev=0 2>/dev/null` (or all commits up to `HEAD` if no prior tag exists) to determine the non-overlapping commit range `<prev_tag>..HEAD`.
- Compile structured Release Notes for the tag annotation and report:
  1. Title: `Release <tag_name>`
  2. Functional Overview (功能概述): Summarize key capabilities, architectural designs, features, and fixes included strictly within this milestone range.
  3. Related Commit Tree (提交历史): Include the exact non-overlapping commit list using `git log <range> --oneline` or formatted bullet tree `* <hash> <subject>`. Never repeat commits included in previous tags.
- Create an annotated Git tag with `git tag -a <tag_name> -m "<release_notes>"` containing the full Release Notes. If the tag already exists, stop and inform the user without using `--force`.
- Automatically push to remote with tags: `git push origin <branch> --tags` (using the current branch name, e.g., `master` or `main`).
- Delete the local tag after the push succeeds: `git tag -d <tag_name>`.
- Report the complete release notes. For non-milestone commits, never push, suggest, or mention pushing.

After the safety checks and language selection, create the commits and tags without requesting unnecessary confirmation. Report every original commit message in execution order, then summarize the total changed lines as additions and deletions.
