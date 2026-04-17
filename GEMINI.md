 已知本项目是codex-skill项目目录，需要你把用户输入的内容转换成 codex skills 并保存，
1. 需要用户输入以下内容
  唤醒词: 
  功能： 
2. 用户如果没有输入唤醒词，请自行根据功能完成 skill description
3. 请你根据 skill description 检索当前目录下是否已经存在功能相似的 skill，如果存在，如果用户没有明确覆盖，先提示用户是否更新功能
    - 尤其要注意中英文是否冲突，比如 commit_english description 是 'commit', commit_chinese description 是 '提交'，这种也要视为 功能相似; 因为大模型是根据语义来判定的
4. 如果不存在，请你创建一个新的 skill
5. 生成的 skill 尽量简单, 让大模型能够理解即可
6. .prompt 目录下，用 {skill_name}.md 文件保存我给你的提示词原文; 后续修改使用{skill_name}_{hhmmss}.md 保存后续版本; 注意，具体的token/url需替换为xxx
7. a compact description covering:
    - what the skill handles
    - when it should trigger
    - when it should not trigger
    - a few natural trigger phrases users would actually say
8. **description should not include:** 
   - dumping all functionality 
   - expected input/output 
   - success criteria
9. 除非用户特意要求，对应 skill 里面的所有内容， skill.md/代码以及其他所有的内容，都一次性同步修改
10. 以上文件生成后，自动执行 git add，纳入git管理
