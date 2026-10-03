# 对话式安装规则

根目录 [`SKILL.md`](../SKILL.md) 是总入口。用户选择 `00` 至 `05` 或“全部”后，分别执行对应的
[`skills/`](../skills/) 子 Skill。未选择前只展示清单，不修改用户级文件。

## 固定来源

- 工作流 fork：[impecme/sol-luna-engineering-workflow](https://github.com/impecme/sol-luna-engineering-workflow/tree/ada4058bfa2f6a7c718c72d7c2b9c555eb3eea38)
- 工作流上游：[BruceLanLan/sol-luna-engineering-workflow](https://github.com/BruceLanLan/sol-luna-engineering-workflow/tree/ed13d90a055630aa89427b20b8a0a2401dc8a47b)
- 技能：[mattpocock/skills Engineering](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering)
- GitHub/Obsidian 技能：[mathruffian-dot/codex-lazy-packs](https://github.com/mathruffian-dot/codex-lazy-packs/tree/574818e2d80b31807b74fcf62dd5b90b9e46ef3f)
- 第二大脑技能：本仓库 `bundled-skills/codex-second-brain`，版本和 schema 以 `sources.lock.json` 为准

完整版本以仓库根目录的 `sources.lock.json` 为准。

## 目标映射

选择 `00` 时，将第一套来源的以下文件安装到用户级 Codex 目录（通常是 `~/.codex`，Windows 通常是 `%USERPROFILE%\.codex`）：

| 上游路径 | 用户级目标 |
| --- | --- |
| `AGENTS.md` | `<CodexHome>/AGENTS.md` |
| `.codex/config.toml` | `<CodexHome>/config.toml` |
| `.codex/agents/luna-worker.toml` | `<CodexHome>/agents/luna-worker.toml` |
| `.codex/agents/sol-advisor.toml` | `<CodexHome>/agents/sol-advisor.toml` |

选择 `01` 时，将第二套来源的以下 18 个目录安装到用户级 Skill 目录（默认 `<CodexHome>/skills`，如当前 Codex 使用其他用户级 Skill 目录，以实际发现的目录为准）：

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

选择“全部”时，按 `00`、`01`、`02`、`03`、`04`、`05` 的顺序执行。

选择 `02` 至 `04` 时，安装第三个来源中的以下 Skill。安装阶段只复制固定版本的 Skill
目录，不执行这些 Skill 的登录、推送、MCP 配置或 Vault 写入动作：

| 懒人包 | 固定来源路径 | 用户级目标目录 |
| --- | --- | --- |
| `02` | `skills/03-github` | `<SkillRoot>/codex-github` |
| `03` | `skills/05-obsidian` | `<SkillRoot>/codex-obsidian` |
| `04` | `skills/04-github-obsidian` | `<SkillRoot>/codex-github-obsidian` |

选择 `05` 时，将本仓库的 `bundled-skills/codex-second-brain` 完整安装到
`<SkillRoot>/codex-second-brain`，并将
`bundled-skills/codex-second-brain/assets/global-agents-section.md` 合并到
`<CodexHome>/AGENTS.md`。这一步不会定位 Vault、建设目录、写设备配置、配置同步或创建每周任务。

其中 `<SkillRoot>` 默认是 `<CodexHome>/skills`。

## 冲突处理

### 配置文件

1. 先读取现有文件并与固定 commit 中的文件比较。
2. 无差异则标记 `already-current`，不重复写入。
3. 有差异则把现有文件备份到 `<CodexHome>/lazy-pack/backups/<timestamp>/`，并展示差异。
4. 通过对话让用户选择：手动合并、使用上游版本、保留现有版本。
5. 手动合并完成后再次读取目标文件，确认写入结果；用户未确认时保持 `pending`。

不要为了合并 TOML 而猜测用户配置的语义；无法安全自动合并时，保留双方文件并让用户决定。

### `AGENTS.md` 受管区块

第二大脑全局规则由以下稳定标记包围：

```text
<!-- codex-second-brain-managed:start -->
...
<!-- codex-second-brain-managed:end -->
```

1. 写入前读取并备份整个 `<CodexHome>/AGENTS.md`，展示新建、追加或替换区块的差异。
2. 标记不存在时，在用户确认后把源区块追加到文件末尾；不要修改其余规则。
3. 标记恰好存在一次时，只比较并原位更新该区块；内容相同则标记 `already-current`。
4. 标记残缺、嵌套或重复时停止自动修改，保留原文件并报告 `pending`。
5. 安装或更新 `00` 的工作流 `AGENTS.md` 时保留该受管区块；执行“全部”时先安装 `00`，再由 `05` 合并或更新区块。

### 同名 Skill

1. 比较目录中的文件和内容；相同则标记 `already-current`。
2. 不同则先展示新增、删除和修改的路径。
3. 用户选择替换时，先备份整个现有 Skill 目录。
4. 用户选择手动合并时，保留上游目录作为候选，并报告需要用户完成的合并。
5. 用户选择跳过时不改变现有 Skill。

## 安装后报告

至少报告：

- 实际执行的懒人包编号。
- 实际执行来源使用的 commit（只报告实际执行的来源）。
- `00` 的 4 个工作流文件、`01` 的 18 个 Skill，以及 `02` 至 `05` 的逐项状态。
- 用户级 Codex 目录和 Skill 目录。
- 备份目录、待处理冲突和需要重启 Codex 的提示。
- 未执行的插件/MCP/凭证配置。

对于 `02` 至 `04`，还要报告目标 Skill 目录、源目录、固定 commit、是否发生备份、
是否需要重启 Codex，以及安装阶段明确未执行的 GitHub 登录、push、MCP 配置和 Vault 写入。
对于 `05`，报告懒人包版本、可解析时的本仓库 commit、内置源目录、目标 Skill 目录、备份位置，
`AGENTS.md` 受管区块状态，并明确尚未执行 Vault 初始化、Syncthing/GitHub 配置或定时任务创建。说明全局规则只有在设备配置
存在且 Vault 可访问后才会自动融入项目工作。

安装阶段不运行已复制 Skill 的正文指令。`02` 至 `04` 之后由用户主动触发；`05` 完成一次性设备配置后由全局规则
在普通项目工作中自动调用。所有已安装 Skill 仍需遵守各自确认边界；尤其不能把 token、密码或其他凭证写入仓库、
`AGENTS.md` 或笔记。
