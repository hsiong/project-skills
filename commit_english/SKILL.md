---
name: "commit_english"
description: "Use when the user says \"英文 commit\", \"english commit\", \"commit\", or similar. This skill makes multiple commits in the current Git workspace using only Git-known files: commit messages must be in English, follow GitHub/Conventional Commits style, group changes by complete functional flow rather than by code module, and be committed from largest change set to smallest. Never access untracked files, never read or commit `*/application.yml`, `*/application-*.yml`, `.fastRequest/*`, `.mvn/*`, `.idea/*`, `config/.env.*`, or anything ignored by `.gitignore`, never modify user code, and always summarize the total changed lines at the end."
---

# Commit

## When to Use

- The user wants you to commit the current workspace directly.
- The user wants you to split the work into multiple commits by feature.
- The user wants English commit messages and expects you to run the commits.

## Hard Constraints

- Only perform commit-related actions. Do not modify user code, clean up files, or fix unrelated issues.
- Only inspect Git-known paths: tracked changes, staged new files, and staged deletions. Never access truly untracked files.
- Never use `git add .`, `git add -A`, `git commit -a`, or any command that broadens scope implicitly.
- Never read or commit the following:
  - `*/application.yml`
  - `*/application-*.yml`
  - `.fastRequest/*`
  - `.mvn/*`
  - `.idea/*`
  - `config/.env.*`
  - Anything matched by `.gitignore`
- Read `.gitignore`. Do not access or commit anything ignored there.
- Never access files that are not already under Git management.

## Safe Workflow

1. Record the baseline commit first:

```bash
BASE_HEAD=$(git rev-parse HEAD)
```

2. Inspect only Git-known changes and hide untracked files:

```bash
git status --short --untracked-files=no
```

3. Every `diff`, `stat`, or `name-only` command must include exclusion rules. Reuse this pathspec:

```bash
-- . \
':(glob,exclude)**/application.yml' \
':(glob,exclude)**/application-*.yml' \
':(glob,exclude)**/.fastRequest/**' \
':(glob,exclude)**/.mvn/**' \
':(glob,exclude)**/.idea/**' \
':(glob,exclude)**/config/.env.*'
```

## Grouping Rules

- Use a complete functional flow as one commit unit, not directory structure, layered modules, or technical components.
- If one business feature touches `controller`, `service`, `impl`, `feign`, `dto`, tests, and docs, prefer one commit for that full flow.
- If multiple features exist, commit them from the largest change set to the smallest.
- Estimate change size by total added and deleted lines in each feature group, using `git diff --numstat` and `git diff --stat` first.
- Docs, style, build, config, and tests can be separate commits only when they form an independent functional flow.

## Commit Message Rules

- Use English only.
- Follow common GitHub commit conventions. Prefer: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`, `build`, `ci`, `perf`.
- Keep the title short, direct, and action-oriented. Do not include file names or numeric prefixes.
- If a one-line subject is not enough, add a short body with hyphen bullets. Do not number the bullets.
- Do not split the message into low-level technical layers. Describe the complete business action first.

Examples:

```text
feat: add internal app access token support
```

```text
docs: document the automated group creation flow

- add the required group-management permission notes
- add the phone-to-userId lookup caveats
- add the group creation and bot binding steps
```

## Output Requirements

- Before committing, list the planned functional groups from largest to smallest. Do not include file names and do not number them.
- After committing, list the actual commit results in commit order, one commit message per line.
- End with a total line summary. Preferred format:

```text
Total changed lines: 123 (+100 / -23)
```

## Failure Handling

- If untracked files might affect the judgment, ignore them and do not inspect their contents.
- If restricted paths contain changes, state clearly that those changes were excluded and not committed.
- If the commits cannot be split safely without violating the constraints, stop and explain why.
