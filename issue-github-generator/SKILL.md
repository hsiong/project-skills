---
name: issue-github-generator
description: "当用户要按当前 Git 改动生成 GitHub issue 草稿或明确要求提交 issue 时触发，例如“生成 issue”“根据这次改动提 issue”“按功能拆 issue”“先查重再写 GitHub issue”“提交这些 issue”。它处理当前工作区内允许访问的 Git 已知改动，按功能拆分、联网查重并生成英文 issue；不用于代码审查、规划新需求、修改代码或提交 commit。"
---

# GitHub Issue Generator

## 适用场景

- 用户要你根据当前工作区生成 GitHub issue 草稿。
- 用户要你尽量按功能拆成多个 issue。
- 用户要你先查重，再生成英文 issue。
- 用户明确要求提交 issue 时，按草稿文件调用脚本提交。

## 分组规则

- 除了纯编程代码以外（`.java`/`.py` 等），不同文件（路径不同或名称不同）分成不同 issue。
- 多个 issue 并存时，按改动量从大到小排序后依次处理。
- 改动量以该功能分组的增删行总数估算，优先看 `git diff --numstat` 和 `git diff --stat`。

### 编程代码分组规则

- 可以按同一业务功能生成一个 issue：
  - 同一业务功能必须是颗粒度很细的具体业务，比如 `集成一个三方接口` 或 `单表 CRUD` 涉及的 controller、service、impl、feign、dto、测试、文档等。
  - 多个三方接口、多表 CRUD 或不同业务模块，不能视为同一业务。
  - 描述里出现 `/`、`和`、`及`、`以及`、`并`、`等` 这类并列关系时，优先拆分。
- 不同业务功能分成不同 issue。
- 难以判断该合并还是拆分时，优先拆成更小的独立 issue。
- 除非单个文件只涉及一个不可拆的修改，否则 issue 正文必须写清具体变更依据。

## 执行流程

1. 获取 Git 已知改动：
   - 如果用户指定 commit、branch、PR、文件或目录，只读取对应范围。
   - 如果没有可用 diff，停止并说明缺少 Git 修改上下文。
   - 获取 diff 前不要做代码审查、架构扫描或顺手分析。

2. 过滤禁区路径：
   - 禁区路径有改动时，只说明已排除，不读取内容，不提交 issue。
   - 未跟踪文件一律忽略。

3. 按功能拆分候选 issue：
   - 先列出候选主题，再确定边界。
   - 每个候选记录对应文件和 diff 依据。

4. 查重：
   - 先查重，后起草。只要仓库可访问，就必须先联网检查现有 issues。
   - 优先使用 `gh issue list`、GitHub API 或网页搜索目标仓库 issue。
   - 关键词来自候选的模块名、接口名、异常信息、行为变化和标题核心词。
   - 已有明显相似 issue 时，不重复起草，直接记录已有 issue 链接、相似点和差异点。

5. 生成 issue 草稿：
   - 生成草稿前，先清空 `docs/issue` 目录下的所有文件。
   - 对每个非重复候选生成标题和 Markdown 正文。
   - 信息不足但可从 diff 推断时合理补全；无法推断时使用简短 `TODO` 占位。
   - 将草稿写入当前仓库的 `docs/issue/` 目录，每个 issue 一个 `.md` 文件。
   - 文件命名为 `docs/issue/<type>-<short-kebab-title>.md`；如同名冲突，追加 `-2`、`-3`。
   - 这些草稿文件不属于 commit 范围。

6. 提交 issue：
   - 只有用户明确要求提交 issue 时，才直接调用本 skill 的 `scripts/submit_issues.sh`。
   - 调用前确认草稿已写入 `docs/issue/`。
   - 脚本参数优先使用目标仓库 `owner/repo` 和草稿目录：`bash scripts/submit_issues.sh <owner/repo> docs/issue`。
   - Token 必须来自 `GITHUB_TOKEN` 或 `GH_TOKEN` 环境变量。

## 输出要求

- 只生成草稿文件，不提交远程 issue。
- 生成后按处理顺序列出草稿文件路径、issue 标题和对应改动范围。
- 对跳过的重复候选，列出现有 issue 链接、相似点和差异点。
- 如果用户明确要求提交，提交后列出 issue 标题、GitHub 链接和对应改动范围。

## 失败处理

- 若仓库无法识别或没有远程 GitHub 地址，停止并说明需要目标仓库。
- 若用户要求提交但缺少 token，停止并说明需要 `GITHUB_TOKEN` 或 `GH_TOKEN`。
- 若发现未跟踪文件可能影响判断，忽略它们，不访问其内容。
- 若无法在不违反约束的前提下安全拆分 issue，停止执行并说明原因。

## Issue 内容要求

- Issue 标题、正文和最终 issue 相关输出必须使用英文。
- 标题使用 GitHub 常见 issue 前缀，优先选择：`Bug:`、`Feature:`、`Refactor:`、`Docs:`、`Chore:`、`Test:`。
- 标题简单直接具体，不写文件名，不写序号。
- 正文使用 Markdown，短横线列点，不要编号。
- 不要把任务理解为“检查现有代码有什么问题并提出 issue”；issue 内容只能来自对应 Git 修改。
- 优先遵循仓库 `.github/ISSUE_TEMPLATE/*`等模板要求。
- 如果没有模板要求，参考下面使用简洁结构。
Bug 类结构：

```markdown
# Summary

# Steps to Reproduce

# Expected Behavior

# Actual Behavior

# Impact
```
- 生成文件名: 标题.placeFirst(":", "-").replace(" ", "-")

## 强约束

- 只做 issue 草稿和提交相关操作，不改用户代码，不顺手修问题，不执行 commit。
- 只允许查看 Git 已知路径：已跟踪改动、已暂存新增、已暂存删除。
- 禁止使用 `git add .`、`git add -A`、`git commit -a`。
- 禁止读取或提交以下内容：
  - `*/application.yml`
  - `*/application-*.yml`
  - `*/.fastRequest/*`
  - `*/.mvn/*`
  - `*/.idea/*`
  - `*/docs/*`
  - `config/.env.*`
  - `.gitignore` 中提到的内容
- 读取 `.gitignore`。禁止访问和提交 `.gitignore` 内提到的内容。
- 如果变更的代码中存在 `todo`，默认必须提醒用户（哪个文件：哪行代码）并终止后续 issue 提交。
- 没有加入到 git 管理中的文件，禁止访问和自行添加。
- 新增的 issue 文件, 无需 `git add`。
- 如果没法直接提交 GitHub issue, 生成英文 issue 草稿到 docs/issue