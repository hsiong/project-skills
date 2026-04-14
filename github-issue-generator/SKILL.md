---
name: github-issue-generator
description: "当用户要生成 GitHub issue 时触发，例如“先查重再写 issue”“按仓库模板起 issue”“帮我生成 issue 草稿”。它负责联网查重并按仓库模板或通用结构生成英文 Markdown 草稿；不用于默认直接提交远程 issue，除非用户明确要求。"
---

# GitHub Issue Generator

## 适用场景

- 用户要你为某个 GitHub 仓库撰写 issue。
- 用户要求先检查是否已有类似 issue，再决定是否新建。
- 用户要求 issue 内容遵循仓库模板、使用英文、输出 Markdown。

## 强约束

- 先查重，后起草。只要仓库可访问，就必须先联网检查现有 issues。
- 若已有明显相似 issue，默认不重复起草，直接返回已有 issue 链接、相似点和差异点。
- 优先遵循仓库自己的 `.github/ISSUE_TEMPLATE`、issue forms 或模板约束。
- 如果仓库没有模板，再使用通用结构起草，标题前缀按类型选择：`Bug:`、`Feature:`、`Refactor:`、`Docs:`、`Question:`。
- 输出语言必须是英文。
- 输出格式必须是 Markdown。
- 默认只输出草稿，不直接调用 GitHub API 或网页操作去提交 issue，除非用户明确要求。

## 工作流

1. 从当前对话中提炼 issue 所需上下文：
   - 目标仓库
   - 问题现象或需求目标
   - 影响范围
   - 复现步骤、期望行为、实际行为、环境信息

2. 联网查重：
   - 优先搜索目标仓库的 GitHub issues。
   - 关键词基于报错信息、核心行为、模块名、特性名组合。
   - 若仓库启用了 discussions，必要时一并检查是否已有同类讨论。

3. 判断是否重复：
   - 若已有高度相似 issue，返回：
     - 相似 issue 链接
     - 相似原因
     - 当前问题与已有 issue 的差异
   - 除非用户要求仍然新建，否则不再继续起草新 issue。

4. 读取本地仓库模板：
   - 优先检查 `.github/ISSUE_TEMPLATE/` 下的 `.md`、`.yml`、`.yaml` 模板。
   - 若存在 issue form，按字段语义转写为 Markdown 草稿。
   - 若存在多个模板，选择与当前类型最匹配的模板。

5. 生成 issue 草稿：
   - 保留模板要求的标题、复选框、段落结构和字段语义。
   - 信息不足时，优先根据上下文合理补全。
   - 若关键事实缺失且无法安全推断，使用简短占位符，例如 `TODO: add reproduction details`。

## 默认输出结构

若仓库无模板，可按下列结构生成：

```markdown
# Title

## Summary

## Steps to Reproduce

## Expected Behavior

## Actual Behavior

## Environment

## Additional Context
```

特性类 issue 可改为：

```markdown
# Title

## Summary

## Problem

## Proposed Change

## Alternatives Considered

## Additional Context
```

## 输出要求

- 只输出最终需要给用户的 Markdown 结果。
- 如果发现相似 issue，优先输出“已有相似 issue”结论和链接列表。
- 如果起草新 issue，输出应可直接复制到 GitHub。
- 不要输出中文解释，不要附加多余操作说明，除非用户额外要求。
