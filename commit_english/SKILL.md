---
name: "commit_english"
description: "Use this skill when the user asks for English Git commits, such as \"English commit\", \"commit this\", or \"split these commits\". It handles only allowed Git-known changes, splits independent work into separate English Conventional Commits, and adds a concrete commit body when one commit covers multiple coordinated subchanges; do not use it to edit code, inspect untracked files, or include restricted paths. Success means the workspace is committed safely by functional flow with clear commit messages and changed-line totals."
---

# Commit

## Applicable Scenarios

- The user wants you to commit the current workspace directly.
- The user wants you to split the work into multiple commits by function.
- The user wants you to generate English commit messages and execute the commits.

## Hard Constraints

- Only perform commit-related operations. Do not modify user code, fix issues on the side, or clean up formatting.
- Only inspect Git-known paths: tracked changes, staged new files, and staged deletions. Truly untracked files must never be accessed.
- Never use commands such as `git add .`, `git add -A`, or `git commit -a` that would broaden the scope.
- Never read or commit the following content:
  - `*/application.yml`
  - `*/application-*.yml`
  - `.fastRequest/*`
  - `.mvn/*`
  - `.idea/*`
  - `config/.env.*`
  - Anything mentioned in `.gitignore`
- Read `.gitignore`. Do not access or commit anything mentioned in `.gitignore`.
- Files that have not been added to Git management must never be accessed.

## Safe Workflow

1. Record the baseline commit first:

```bash
BASE_HEAD=$(git rev-parse HEAD)
```

2. Inspect only Git-known changes and hide untracked files:

```bash
git status --short --untracked-files=no
```

3. All `diff`, `stat`, and `name-only` commands must include exclusion rules to avoid restricted paths. Reuse the following pathspec:

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

- Use a complete functional flow as one commit unit. Do not split by code directory, layered module, or technical component.
- One commit must correspond to one concrete task or one user intent. If the summary naturally contains "and", treat that as a warning sign that the changes should probably be split.
- Changes to different peer features, skills, or modules are independent by default, even if they are all docs, prompts, or metadata updates.
- Only keep multiple peer targets in one commit when they are the same coordinated standards update applied consistently across those targets.
- If several peer targets stay in one commit, the commit message body must list the concrete subchanges. A vague umbrella title alone is not acceptable.
- If the same business function involves `controller`, `service`, `impl`, `feign`, `dto`, tests, and documentation, prefer grouping them into the same commit.
- Documentation, examples, prompts, tests, or metadata may be grouped with code only when they are directly supporting that exact same function. If they introduce a second topic, they must be split out.
- README updates, repository guidance, or cross-skill documentation must not be mixed into a feature commit unless they are strictly describing that same single feature and nothing else.
- When multiple functions coexist, commit them in order from the largest change set to the smallest.
- Estimate change size by the total added and deleted lines in each functional group, prioritizing `git diff --numstat` and `git diff --stat`.
- Documentation, style, build, config, test, and similar changes may be committed separately only when they form an independent functional flow.
- When uncertain between one commit and multiple commits, prefer splitting into smaller independent commits rather than mixing unrelated work.

## Commit Message Requirements

- Use English only.
- Follow common GitHub commit conventions. Prefer: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`, `build`, `ci`, `perf`.
- Keep the title as short, direct, and actionable as possible. Do not include file names and do not include sequence numbers.
- If a single-line title is not enough to express the change, add a short body; use hyphen bullets in the body and do not use numbering.
- When one commit covers multiple coordinated subchanges under the same main flow, a bullet body is required and each bullet must describe one concrete subchange.
- Titles like `chore: refresh skill descriptions and prompts` are incomplete on their own when multiple skills or modules were updated; either split the commits or add bullets such as `- refresh commit_chinese description`.
- If the required bullet list starts describing separate intentions instead of one coordinated flow, split the work into multiple commits.
- Do not split low-level technical layers into multiple points. Prefer describing the complete business action.

Examples:

```text
feat: add internal app access token support
```

```text
docs: document the automated group creation flow

- add the group management permission application notes
- add the phone number to userId lookup caveats
- add the group creation and bot binding flow
```

```text
chore: align skill metadata wording

- refresh commit_chinese description and default prompt
- refresh commit_english description and default prompt
- tighten Java and Python skill summaries for minimal-change guidance
```

## Output Requirements

- Before committing, explicitly check that each planned commit contains only one independent topic.
- Before committing, explicitly decide whether each planned commit can stand as a title-only commit or requires a bullet body.
- Before committing: list the planned functional groups from the largest change set to the smallest. Do not include file names and do not add numbering.
- After committing: provide the actual commit results and list each commit message in commit order.
- Finally summarize the total changed lines. Recommended format:

```text
Total changed lines: 123 (+100 / -23)
```

## Failure Handling

- If untracked files may affect the judgment, ignore them and do not access their contents.
- If there are changes under restricted paths, clearly state that those changes were excluded and were not included in the commits.
- If it is impossible to split commits safely without violating the constraints, stop execution and explain the reason to the user.
