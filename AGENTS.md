 已知本项目是codex-skill项目目录，需要你把用户输入的内容转换成 codex skills 并保存，
1. 需要用户输入以下内容
唤醒词: 
功能： 
2. 用户如果没有输入唤醒词，请自行根据功能完成 skill description
3. 请你根据 skill description 检索当前目录下是否已经存在功能相似的 skill，如果存在，如果用户没有明确覆盖，先提示用户是否更新功能
4. 如果不存在，请你创建一个新的 skill
5. 生成的 skill 尽量简单, 让大模型能够理解即可
6. .prompt 目录下，用 {skill_name}.md 文件保存我给你的提示词原文