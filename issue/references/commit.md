# Issue Commit

Directly push Git changes to remote `fix/issue_code` branches linked to GitHub issues, without creating or retaining local branches or commits.

## Workflow

1. **Parse Input**:
   - Extract issue numbers (e.g., `#25`) and issue titles from the prompt.
   - If the user provides only "issue commit:" without subsequent issue information, halt and request issue details.

2. **Diff Mapping**:
   - Map workspace modified files to the most relevant issue.

3. **Atomic Push (Zero Local Footprint)**:
   - For each issue and its mapped files, run:
     1. **Commit**: `git commit -m "<keyword>: <issue_title_summary>(#<issue_code>)" <file_list>`
        - Strip prefixes (`Bug:`, `Feature:`, etc.) from the title.
        - Valid `<keyword>` verbs: `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`.
     2. **Push**: `git push origin HEAD:fix/<issue_code>`
     3. **Reset**: `git reset --soft HEAD~1` (reverts the commit locally while keeping modifications staged, leaving zero local commit history).

4. **Summary & Pull Request Link**:
   - List successfully pushed branches and mapped files.
   - Provide a GitHub Pull Request URL for each branch:
     ```text
     Create Pull Request: https://<repo_url>/pull/new/<branch_name>
     Description: <keyword>: #<issue_code>
     ```

## Strict Constraints

- **Zero Local Branches**: Never run `git checkout -b` or `git branch` to create local branches.
- **Direct Remote Update**: Always update remote refs via `HEAD:<remote_branch>`.
- **Local State Preservation**: Always run `git reset --soft` after push so working directory changes remain intact.
