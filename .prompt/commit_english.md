Use this skill when the user says "English commit", "english commit", "commit", or similar.

1. Complete multiple commits in the current Git workspace using only Git-known files.
2. All commit messages must be in English and follow GitHub/Conventional Commits style.
3. Group changes by complete functional flow rather than by code module, and never mix independent topics in one commit.
4. One commit must represent one concrete task or one user intent. Docs, tests, prompts, or metadata can join only when they directly support that same task.
5. If a summary sounds like "do A and do B", split it. When unsure, prefer more smaller commits over one mixed commit.
6. Never access files that are not added to Git, and never read or commit restricted paths or anything mentioned in `.gitignore`.
7. Never modify user code without permission, and summarize the total changed lines after completion.
