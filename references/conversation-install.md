# 对话式安装规则

## 固定来源

- 工作流：[sol-luna-engineering-workflow](https://github.com/BruceLanLan/sol-luna-engineering-workflow/tree/ed13d90a055630aa89427b20b8a0a2401dc8a47b)
- 技能：[mattpocock/skills Engineering](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering)

完整版本以仓库根目录的 `sources.lock.json` 为准。

## 目标映射

将第一套来源的以下文件安装到用户级 Codex 目录（通常是 `~/.codex`，Windows 通常是
`%USERPROFILE%\.codex`）：

| 上游路径 | 用户级目标 |
| --- | --- |
| `AGENTS.md` | `<CodexHome>/AGENTS.md` |
| `.codex/config.toml` | `<CodexHome>/config.toml` |
| `.codex/agents/luna-worker.toml` | `<CodexHome>/agents/luna-worker.toml` |
| `.codex/agents/sol-advisor.toml` | `<CodexHome>/agents/sol-advisor.toml` |

将第二套来源的以下 18 个目录安装到用户级 Skill 目录（默认 `<CodexHome>/skills`，如当前
Codex 使用其他用户级 Skill 目录，以实际发现的目录为准）：

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

## 冲突处理

### 配置文件

1. 先读取现有文件并与固定 commit 中的文件比较。
2. 无差异则标记 `already-current`，不重复写入。
3. 有差异则把现有文件备份到 `<CodexHome>/lazy-pack/backups/<timestamp>/`，并展示差异。
4. 通过对话让用户选择：手动合并、使用上游版本、保留现有版本。
5. 手动合并完成后再次读取目标文件，确认写入结果；用户未确认时保持 `pending`。

不要为了合并 TOML 而猜测用户配置的语义；无法安全自动合并时，保留双方文件并让用户
决定。

### 同名 Skill

1. 比较目录中的文件和内容；相同则标记 `already-current`。
2. 不同则先展示新增、删除和修改的路径。
3. 用户选择替换时，先备份整个现有 Skill 目录。
4. 用户选择手动合并时，保留上游目录作为候选，并报告需要用户完成的合并。
5. 用户选择跳过时不改变现有 Skill。

## 安装后报告

至少报告：

- 两个来源实际使用的 commit。
- 4 个工作流文件和 18 个 Skill 的逐项状态。
- 用户级 Codex 目录和 Skill 目录。
- 备份目录、待处理冲突和需要重启 Codex 的提示。
- 未执行的插件/MCP/凭证配置。
