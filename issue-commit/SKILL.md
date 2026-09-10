---
name: issue-commit
description: "当用户输入包含 issue 标题和编号的内容时触发，例如“issue commit: #25 ...”。它负责解析 issue 信息、将对应改动直接推送到远程 `fix/issue_code` 分支，且完全不创建本地分支；不用于普通无 issue 关联的提交或处理未跟踪文件。"
---

# Issue Commit

## 适用场景

- 用户提供了一个或多个 issue 的详细信息（如从 GitHub 复制的列表），要求按 issue 提交代码。
- 需要将改动直接推送到远程的 `fix/issue_code` 分支，但**完全不需要**在本地创建任何新分支。
- 提交信息需要符合 `keyword: issue_title_summary(#issue_code)` 格式。移除 `issue_title` 中的前缀（如Bug,Feature,Refactor...）
  ```
  keyword 代表某次提交的类型，比如是修复一个bug还是增加一个新的feature。所有的type类型如下：
  close
  closes
  closed
  fix
  fixes
  fixed
  resolve
  resolves
  resolved
  ```

## 核心流程

1. **信息解析**：从输入文本中提取每个 issue 的编号（如 #25）和标题。
2. **输入校验**：如果用户只输入了 "issue commit:" 而没有后续内容，提示用户补充信息。
3. **改动分析**：获取当前工作区所有已跟踪文件的改动。
4. **改动映射**：将每个改动的文件映射到最相关的 issue。
5. **按 Issue 直接推送（不留痕迹）**：
   - 针对每个 issue 及其映射的文件，执行以下原子操作：
     - **提交**：`git commit -m "提交信息" <文件列表>`。
     - **推送**：`git push origin HEAD:fix/issue_code`（将当前分支的最顶端提交推送到远程目标分支）。
     - **回滚**：`git reset --soft HEAD~1`（本地撤销该提交，保留改动。这确保了本地不产生额外的 commit 记录，且不改变分支结构）。
6. **汇总**：列出已成功推送到远程的 issue 分支及其对应的文件清单。推送成功后，自动根据当前仓库的 GitHub 地址和推送的目标分支拼装 Pull Request 创建链接并提示用户：
```
您可以点击下方链接，在 GitHub 上针对该分支创建 Pull Request：
   🔗 创建 Pull Request  https://<repo_url>/pull/new/<branch_name>
   description: keyword: #issue_code
```

## 强约束

- **零本地分支**：严禁使用 `git checkout -b` 或 `git branch` 创建新分支。
- **直接推送远程**：通过 `HEAD:remote_branch` 语法直接更新远程引用。
- **本地状态保持**：推送完成后，通过 `git reset --soft` 确保本地工作区改动依然存在（或处于 staged 状态），不污染本地提交历史。
- 只做 issue 草稿和提交相关操作，不改用户代码，不顺手修问题，不执行 commit。
- 只允许查看 Git 已知路径：已跟踪改动、已暂存新增、已暂存删除。没有加入到 git 管理中的文件，禁止访问和自行添加。
- 禁止使用 `git add .`、`git add -A`、`git commit -a`。
- 禁止读取或提交以下内容：
  - `*/application.yml`
  - `*/application-*.yml`
  - `*/.fastRequest/*`
  - `*/.mvn/*`
  - `*/.idea/*`
  - `*/docs/*`
  - 除了 `.env.example` 外的 `config/.env.*`
  - `.gitignore` 中提到的内容
- 读取 `.gitignore`。禁止访问和提交 `.gitignore` 内提到的内容。
- 如果变更的代码中存在 `todo`，默认必须提醒用户（哪个文件：哪行代码）并终止后续 issue 提交。
- 在任何提交或推送前，扫描全部拟提交文件的最终内容；若发现疑似真实敏感信息，包括认证秘密（密钥、令牌、密码、私钥/证书、Cookie/会话、数据库或云凭据）、个人信息（手机号、个人邮箱、证件号、银行卡号、真人姓名、真人头像或图片 URL、地址/精确定位、健康或生物识别信息）或内部非公开地址/数据，立即终止全部后续提交和推送，仅以遮蔽值报告文件、行号及类型并提醒用户；明确占位符、脱敏样例和虚构测试数据除外。
- 新增的 issue 文件, 无需 `git add`。
- 如果用户未提供 issue 内容，停止执行并提示：“请先输入 issue 标题和编号信息”。
