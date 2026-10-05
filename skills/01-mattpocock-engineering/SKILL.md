---
name: codex-mattpocock-engineering
description: 通过对话安装 mattpocock/skills Engineering 目录中固定 commit 的 18 项工程技能。
---

# Matt Pocock Engineering 技能

仅在用户选择 `01` 或“全部”时执行本 Skill。

## 安装来源

先读取仓库根目录的 [`sources.lock.json`](../../sources.lock.json)，只使用 `mattpocock-engineering` 条目中的 repository、`sourceRoot` 和固定 commit。具体冲突规则见 [`references/conversation-install.md`](../../references/conversation-install.md)。

固定来源：

- 仓库：[mattpocock/skills](https://github.com/mattpocock/skills)
- 来源根目录：`skills/engineering`
- 目标：共享安装规则预检确定的用户级 `<SkillRoot>`。

## 必须安装的 18 项技能

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

## 执行要求

先执行共享安装规则的新设备预检，并读取 [Codex 兼容性说明](../../references/mattpocock-codex-compatibility.md)。
保留上游 `agents/openai.yaml` 的显式调用策略；静态校验告警与客户端加载结果分别记录。

1. 按锁定 commit 获取上述 18 个目录的完整内容，不只复制每个目录的 `SKILL.md`，除非用户明确要求精简安装。
2. 逐个比较目标目录与上游目录。内容相同则标记 `already-current`；不同则先展示新增、删除和修改的路径。
3. 用户选择替换时，先备份整个现有 Skill 目录，再写入上游版本；选择手动合并时，保留上游目录作为候选并将该项标记为 `pending`；选择跳过时保持现有 Skill 不变。
4. 如果当前 Skill 安装能力无法锁定指定 commit，按该 commit 下载对应目录；不得无提示改用 `main`/`master`。
5. 按共享规则逐项报告 18 个 Skill 的文件安装、客户端发现和功能验证状态，以及 commit、目录、备份和缺失依赖；安装阶段不执行项目初始化。

本 Skill 不安装 Luna/Sol 工作流配置，也不安装插件、MCP server 或凭证；只有用户选择“全部”时，根入口才会先执行 `00`，再执行本 Skill。
