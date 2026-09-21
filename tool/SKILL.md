---
name: tool
description: 'Provide daily reports, local HTML-to-JPG conversion, project guides, README optimization, and prompt management (recording and archiving) through one tool skill. Trigger automatically once per day in any project with prompt records, or on "调用工具" with a capability request (such as "调用工具-日报", "调用工具-HTML转JPG", "调用工具-项目指南", "调用工具-优化README", or "调用工具-归档prompt"). Do not trigger prompt archiving more than once per day for the same project unless explicitly forced, and do not trigger other capabilities without "调用工具".'
---

# Tool

## Route the request

Interpret the text after `调用工具` semantically; a hyphen, space, or colon is an optional separator. Use the task context to resolve the intended capability, project, and inputs.

| Capability | Matching words and phrases | Instructions |
| --- | --- | --- |
| Daily report | 日报, 今日日报, 今日行为, 根据今天的问题和改动写日报, daily report | [daily-report.md](references/daily-report.md) |
| HTML to JPG | HTML转JPG, 网页转图片, 本地HTML截图, convert this HTML to JPG | [html-to-jpg.md](references/html-to-jpg.md) |
| Project guide | 项目指南, 项目说明, 所有功能和配置, 从0到1运行使用本项目, complete project guide | [project-guide.md](references/project-guide.md) |
| README optimization | 优化README, 重写README, 添加中文README, rewrite the README, add a Chinese README | [readme-optimizer.md](references/readme-optimizer.md) |
| Prompt recording & archiving | 归档prompt, prompt归档, 保存prompt, 记录prompt, archive prompt, record prompt, or auto once per day | [prompt-archiver.md](references/prompt-archiver.md) |

Read only the selected capability's instructions and the supporting references needed for that task, then execute them. These are internal capabilities of this skill, not separately invoked skills.

Choose the project guide for comprehensive feature, configuration, and startup explanations; choose README optimization when the requested deliverable is a repository README. If multiple capabilities are explicitly requested, perform them in dependency order. If no capability can be identified, briefly list the five choices and ask which one is needed; do not run all five by default.

## Shared execution rules

- Resolve bundled scripts, resources, and `requirements.txt` against this `tool/` directory, independently of the user's target project or shell working directory. Markdown reference links are relative to the containing document.
- For Python helpers, use the project dependency environment and this skill's root `requirements.txt`; never install into global Python. If no project environment exists, create and use `/tmp/tool/bin/python`, then remove the temporary environment when finished. Install dependencies only for capabilities that need the helpers.
- Use copyable multiline shell commands with a trailing backslash on each continued line and no spaces after it. Preserve the user's requested output language and location.
