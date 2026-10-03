---
name: codex-obsidian-pack
description: 通过对话安装固定版本的 codex-obsidian Skill，让 Codex 可以在之后主动配置 Obsidian Vault 访问。
---

# Obsidian Skill 安装包

仅在用户选择 03 或“全部”时执行本 Skill。

## 目标

本子 Skill 只安装参考懒人包中的 codex-obsidian，不在本次安装中寻找、修改或写入 Obsidian Vault。
用户之后可以通过“连接 Obsidian”等对话主动触发已安装的 codex-obsidian。

## 固定来源

先读取仓库根目录的 sources.lock.json，只使用 mathruffian-codex-lazy-packs 条目中的 repository、commit 和 sourcePath。

- 仓库：[mathruffian-dot/codex-lazy-packs](https://github.com/mathruffian-dot/codex-lazy-packs)
- 固定 commit：以 sources.lock.json 中的 574818e2d80b31807b74fcf62dd5b90b9e46ef3f 为准
- 源目录：skills/05-obsidian
- 目标目录：<SkillRoot>/codex-obsidian

<SkillRoot> 默认是 <CodexHome>/skills；如果当前环境使用其他用户级 Skill 目录，以实际发现的目录为准。

## 执行要求

1. 按固定 commit 获取源目录的完整内容，不无提示改用 main 或 master。
2. 读取目标目录和现有文件。目录不存在时直接标记为待安装；内容相同则标记为 already-current。
3. 目标目录已存在且内容不同或来源不明时，先展示新增、删除和修改的路径，再备份整个目录。
4. 通过对话让用户选择替换、手动合并或跳过；未确认时保持 pending，不要静默覆盖。
5. 替换或合并后重新读取目标 Skill，确认 frontmatter、目录结构和内容均可读。
6. 安装阶段只复制 Skill，不运行 npm、npx、codex mcp add，不授权 Vault，也不重启 Codex。

## 安全边界与报告

不要索要或保存 Obsidian API token、密码、Vault 私密信息或其他凭证。安装完成后报告固定 commit、源目录、目标目录、状态、备份位置和是否需要重启 Codex。
如果用户想实际连接 Obsidian，应在本 Skill 完成后让用户主动触发已安装的 codex-obsidian，并先确认具体 Vault 路径和访问方式。
