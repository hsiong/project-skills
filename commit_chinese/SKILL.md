---
name: commit_chinese
description: 当用户说“日常commit”“中文commit”或类似指令时使用。该技能负责在当前 Git 工作区内，仅基于 Git 已知文件完成多次提交：提交信息必须是中文、遵循 GitHub/Conventional Commits 风格、按完整功能链路分组而不是按代码模块分组，并按改动量从大到小排序。严禁访问未加入 Git 的文件，严禁读取或提交 `*/application.yml`、`*/application-*.yml`、`.fastRequest/*`、`.mvn/*`、`.idea/*`、`config/.env.*` 以及 `.gitignore` 涉及的内容；严禁擅自修改用户代码；完成后必须汇总总改动行数。
---

# Commit

## 适用场景

- 用户要你直接提交当前工作区。
- 用户要你按功能拆分为多次提交。
- 用户要你生成中文 commit message 并执行提交。

## 强约束

- 只做提交相关操作，不改用户代码，不顺手修问题，不整理格式。
- 只允许查看 Git 已知路径：已跟踪改动、已暂存新增、已暂存删除。真正未跟踪文件一律不访问。
- 禁止使用 `git add .`、`git add -A`、`git commit -a` 这类会扩大范围的命令。
- 禁止读取或提交以下内容：
  - `*/application.yml`
  - `*/application-*.yml`
  - `.fastRequest/*`
  - `.mvn/*`
  - `.idea/*`
  - `config/.env.*`
  - `.gitignore` 中提到的内容
- 读取 `.gitignore`。禁止访问和提交 .gitignore 内提到的内容
- 没有加入到 git 管理中的文件，禁止你访问

## 安全工作流

1. 先记录基线提交：

```bash
BASE_HEAD=$(git rev-parse HEAD)
```

2. 只查看 Git 已知改动，隐藏未跟踪文件：

```bash
git status --short --untracked-files=no
```

3. 所有 diff、stat、name-only 命令都必须附带排除规则，禁止碰禁区路径。可复用下面这组 pathspec：

```bash
-- . \
':(glob,exclude)**/application.yml' \
':(glob,exclude)**/application-*.yml' \
':(glob,exclude)**/.fastRequest/**' \
':(glob,exclude)**/.mvn/**' \
':(glob,exclude)**/.idea/**' \
':(glob,exclude)**/config/.env.*'
```

## 分组规则

- 以完整功能链路为一个提交单元，不按代码目录、分层模块或技术组件拆分。
- 同一业务功能涉及 `controller`、`service`、`impl`、`feign`、`dto`、测试、文档时，优先归为同一提交。
- 多个功能并存时，按改动量从大到小排序后依次提交。
- 改动量以该功能分组的增删行总数估算，优先看 `git diff --numstat` 和 `git diff --stat`。
- 纯文档、样式、构建、配置、测试等若形成独立功能链路，可单独提交。

## 提交信息要求

- 全部使用中文。
- 符合 GitHub 常见提交规范，优先使用：`feat`、`fix`、`docs`、`refactor`、`style`、`test`、`chore`、`build`、`ci`、`perf`。
- 标题尽量短、直接、可执行，不写文件名，不写序号。
- 若单行标题不足以表达，可加简短正文；正文使用短横线列点，不要编号。
- 不把技术层拆成多个点，优先描述完整业务动作。

示例：

```text
feat: 新增企业内部应用 accessToken 获取能力
```

```text
docs: 完善自动建群功能链路说明

- 补充群管理权限申请
- 补充手机号查 userId 注意事项
- 补充建群并关联机器人流程
```

## 输出要求

- 提交前：列出拟提交的功能分组，按改动量从大到小排列，不写文件名，不加序号。
- 提交后：给出实际提交结果，按提交顺序列出每条 commit message。
- 最后汇总总改动行数，推荐格式：

```text
总计改动 123 行（+100 / -23）
```

## 失败处理

- 若发现未跟踪文件可能影响判断，忽略它们，不访问其内容。
- 若禁区路径中存在改动，明确说明这些内容被排除，不纳入提交。
- 若无法在不违反约束的前提下安全拆分提交，停止执行并向用户说明原因。
