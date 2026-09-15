---
name: issue
description: "Handle GitHub issue and pull request workflows including drafting or submitting issues from Git changes, generating PR drafts from templates, and pushing commits directly to issue-linked remote branches. Trigger when users say '生成 issue', '根据这次改动提 issue', '按功能拆 issue', '先查重再写 GitHub issue', '提交这些 issue', 'issue commit', 'issue commit: #...', '生成 pr', '提 pr', '完成 pr', or 'draft pr'. Do not trigger for ordinary commits without issues, standalone code reviews, or untracked file handling."
---

# Issue

Manage GitHub issue and pull request workflows: generating structured, deduplicated issue drafts, generating PR drafts from templates, or pushing code directly to issue-linked remote branches.

## Route the request

Resolve the user's intent to one of the internal capabilities below:

| Capability | Matching words and phrases | Instructions |
| --- | --- | --- |
| Issue Generator | 生成 issue, 提 issue, 根据这次改动提 issue, 按功能拆 issue, 先查重再写 GitHub issue, 提交这些 issue, draft issue, generate issue | [generator.md](references/generator.md) |
| Issue Commit | issue commit, issue commit: #, 按 issue 提交, 推送 issue 分支, push issue branch | [commit.md](references/commit.md) |
| PR Generator | 生成 pr, 提 pr, 完成 pr, 写 pr, 根据改动生成 pr, draft pr, create pr, pull request | [pr.md](references/pr.md) |

Read only the selected capability's instructions and supporting references needed for that task, then execute them. These are internal capabilities of this skill, not separately invoked skills.

If the request is ambiguous between drafting and committing, clarify before executing.

## Shared execution rules & security gates

- **Git Scope**: Inspect only Git-known changes (tracked modifications, staged additions, staged deletions). Completely ignore untracked files without reading or adding them.
- **Excluded Paths**: Never read or commit files matching `application*.yml`, `config/.env.*` (except `.env.example`), `.env`, `docs/.env`, `*/.mvn/*`, `*/.idea/*`, `*/.fastRequest/*`, `docs/*`, or patterns listed in `.gitignore`.
- **TODO Gate**: If candidate diffs contain `TODO` (case-insensitive), immediately halt execution and report the specific file and line number.
- **Sensitive Data Gate**: Prior to staging, committing, or drafting, scan the final content of all candidate files. If suspected secrets, tokens, private keys, credentials, private URLs, or internal endpoints are found, immediately halt and report only the masked location and data type.
- **Boundary**: Perform only issue drafting and issue branch operations. Do not alter unrelated user code, fix unrequested bugs, or create ordinary local commits.
- **Scripts**: Resolve bundled scripts relative to this `issue/` directory (`bash scripts/submit_issues.sh`).
