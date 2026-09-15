# PR Generator

Generate Pull Request (PR) descriptions based on Git branch diffs and repository PR templates.

## Workflow

1. **Retrieve Git Diffs & Commit Context**:
   - Identify the target upstream branch (e.g., `origin/dev` or `origin/master`).
   - Inspect commits and diffs on the current branch compared to upstream (`git log <upstream>..HEAD`, `git diff <upstream>..HEAD --stat`).
   - Halt if there are no branch commits or diffs to summarize.

2. **PR Template Discovery**:
   - Check repository for PR templates in order:
     - `.github/pull_request_template.md`
     - `.github/PULL_REQUEST_TEMPLATE.md`
     - `.github/PULL_REQUEST_TEMPLATE/*.md`
   - If a template exists, strictly preserve its markdown structure, headers, and checklist items.
   - If no template exists, fallback to standard structure:
     - `## Motivation`
     - `## Modification`
     - `## Checklist`

3. **Draft Generation**:
   - Ensure the directory `docs/issue-pr/` exists.
   - **No Title in Body**: The PR draft markdown must NOT include an `# <Title>` line at the top, since GitHub PR creation UI has a dedicated title field.
   - Write comprehensive English content:
     - **Motivation**: Explain why the change is necessary, problem symptoms, and goals.
     - **Modification**: Enumerate specific files, classes, and function changes using markdown bullet points.
     - **BC-breaking**: State whether backward compatibility is broken.
     - **Use cases**: Outline relevant production scenarios.
     - **Checklist**: Mark applicable checks (`[x]`).
   - Save the draft to `docs/issue-pr/<short-kebab-branch-or-summary>.md` (e.g., `docs/issue-pr/fix-cleanup-orphan-output-dirs.md`).
   - These draft files are strictly local output artifacts and must never be staged or committed to Git.

4. **Output Requirements**:
   - Output recommended PR Title (e.g., conventional commit style `fix(scope): ...`).
   - Output draft file path in `docs/issue-pr/`.
   - Output one-click GitHub PR creation URLs:
     - Detect remote fork and upstream remotes (`origin`, `mine`, etc.).
     - Construct compare link: `https://github.com/<upstream_owner>/<repo>/compare/<target_branch>...<fork_owner>:<repo>:<branch_name>?expand=1`
   - Display full PR description content for convenient copying.
