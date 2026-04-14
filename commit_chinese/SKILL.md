---
name: commit_chinese
description: "当用户要按功能做中文 Git 提交时触发，例如“中文 commit”“按功能提交一下”。它处理当前工作区内允许访问的 Git 已知改动；不用于改代码、访问未跟踪文件或提交受限路径。"
---

# Commit

## 适用场景

- 用户要你直接提交当前工作区。
- 用户要你按业务功能拆分为多次提交。
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

## 分组规则

- 不同文件尽量分成不同的提交
  - 纯文档、样式、构建、配置、测试等若形成独立功能，可单独提交
  - 难以判断该合并还是拆分时，优先拆成更小的独立提交，而不是混入无关改动。
  - 除非同一个文件涉及了多个变更，提交正文必须逐条写出具体变更，比如集成的具体接口或者具体的单表业务等等。
- 代码按同一业务功能，进行一次提交：
  - 同一业务功能必须是同一个颗粒度非常细的具体业务，比如 `集成一个三方接口`或者`单表CRUD` 涉及到的 `controller`、`service`、`impl`、`feign`、`dto`、测试、文档等都属于同一业务。
  - 接入多个三方接口或者多表CURD或者不同业务模块，不能视为同一业务
  - 使用了 `/`、`和`、`及`、`以及`、`并`、`等`，不能视为同一业务
- 多个功能并存时，按改动量从大到小排序后依次提交。
- 改动量以该功能分组的增删行总数估算，优先看 `git diff --numstat` 和 `git diff --stat`。

## 提交信息要求

- 全部使用中文。
- 符合 GitHub 常见提交规范，优先使用：`feat`、`fix`、`docs`、`refactor`、`style`、`test`、`chore`、`build`、`ci`、`perf`。
- 标题简单直接具体，不写文件名，不写序号。
- 使用短横线列点，不要编号。

示例：

```text
feat: 新增企业内部应用 accessToken 获取能力
```
+ 同一个文件
```text
docs: 完善自动建群功能说明

- 补充群管理权限申请说明
- 补充手机号查 userId 注意事项说明
- 补充建群并关联机器人流程说明
```

## 输出要求

- 提交后：按提交顺序列出每条 commit 的原始文本。
- 最后汇总总改动行数，推荐格式：

```text
总计改动 123 行（+100 / -23）
```

## 失败处理

- 若发现未跟踪文件可能影响判断，忽略它们，不访问其内容。
- 若禁区路径中存在改动，明确说明这些内容被排除，不纳入提交。
- 若无法在不违反约束的前提下安全拆分提交，停止执行并向用户说明原因。
