 已知本项目是codex-skill项目目录，需要你把用户输入的内容转换成 codex skills 并保存，
1. 需要用户输入以下内容
  唤醒词: 
  功能： 
2. 用户如果没有输入唤醒词，请自行根据功能完成 skill description
   - 如果用户...
3. 请你根据 skill description 检索当前目录下是否已经存在功能相似的 skill，如果存在，如果用户没有明确覆盖，先提示用户是否更新功能
    - 尤其要注意中英文是否冲突，比如 commit_english description 是 'commit', commit_chinese description 是 '提交'，这种也要视为 功能相似; 因为大模型是根据语义来判定的
4. 如果不存在，请你创建一个新的 skill
5. 生成的 skill 尽量简单, 并使用英文, 让大模型能够理解即可
6. skill 中存在 Python 脚本时，必须在该 skill 根目录配置 `requirements.txt`，并与 Python 代码依赖同步更新；执行测试或运行时，应使用项目依赖，禁止使用全局 pip 污染全局依赖；没有项目环境时使用临时环境 `/tmp/项目名/bin/python`，临时环境结束后要移除
7. a compact description covering:
    - what the skill handles
    - when it should trigger
    - when it should not trigger
    - a few natural trigger phrases users would actually say
8. **description should not include:** 
   - dumping all functionality 
   - expected input/output 
   - success criteria
9. 对应 skill 里面的所有内容， skill.md/代码以及其他所有的内容，都一次性同步修改
10. 以上文件生成后，自动执行 git add，纳入git管理
11. `SKILL.md` 不能包含重复的内容或重复的指令, 已经提过的, 后文就不要再重复提
12. .prompt 目录下，用 {skill_name}.md 文件保存我给你的提示词原文; 后续修改使用{skill_name}_{hhmmss}.md 保存后续版本; 注意，具体的token/url需替换为xxx; 该文件不加入git管理
