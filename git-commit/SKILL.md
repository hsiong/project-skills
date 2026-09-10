---
name: git-commit
description: "Handle local Git commits in Chinese or English when users say commit, 提交, 中文 commit, English commit, or ask to split changes into commits. Do not trigger for code editing, issue-linked push workflows, untracked-file inspection, or push-only requests."
---

# Git Commit

Create focused conventional commits from the repository's Git-known changes.

## Language

- Follow an explicit request for Chinese or English commit messages.
- Otherwise match the language of the user's request. For mixed or language-neutral requests, default to English.
- Keep the commit message entirely in the selected language, apart from the conventional commit type.

## Scope

- Perform commit operations only. Do not edit code, reformat files, or fix unrelated problems.
- Inspect only tracked changes, staged additions, and staged deletions. Ignore untracked files without reading their contents.
- Read `.gitignore`, but do not access or commit ignored content.
- Exclude `*/application.yml`, `*/application-*.yml`, `*/.fastRequest/*`, `*/.mvn/*`, `*/.idea/*`, `*/.antigravity/*`, `*/.vscode/*`, `*/.git/*`, `config/.env.*` (except `.env.example`), and `*/.DS_Store`.
- Never run `git push`; use the issue-specific commit workflow instead when an issue number and remote branch are part of the request.

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

After the safety checks, create the commits without requesting another confirmation. Report every original commit message in execution order, then summarize the total changed lines as additions and deletions.
