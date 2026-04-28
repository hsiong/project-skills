daily_report 有问题  `~/.codex/sessions/$(date +%Y/%m/%d)/*.jsonl` 是面向所有项目的   但是 git log  只是当前项目, 我该怎么优化呢?   因为 `~/.codex/sessions/$(date +%Y/%m/%d)/*.jsonl` 会遗漏我自己手动修改的部分   你先不要优化  给我说下思路

有没有方式  git 能读取到今天所有的提交  不同项目

`~/.codex/sessions/$(date +%Y/%m/%d)/*.jsonl` 那能获取到运行的目录吗 ?

核心就是：session 负责发现从对话历史中提取用户当天输入的问题、需求、报错、改动意图，以及 assistant 最终完成的任务摘要, 并从`  - session_meta.payload.cwd：这次 Codex 会话启动时的目录。` 反推git目录，再从Git 负责确认这些项目实际改了什么。 其中git会包括一些用户修改的内容, 而不完全是 codex 的内容

按这个改  核心就是：session 负责发现从对话历史中提取用户当天输入的问题、需求、报错、改动意图，以及 assistant 最终完成的任务摘要, 并从`  - session_meta.payload.cwd：这次 Codex 会话启动时的目录。` 反推
  git目录，再从Git 负责确认这些项目实际改了什么。 其中git会包括一些用户修改的内容, 而不完全是 codex 的内容
