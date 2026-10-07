# 对话式安装规则

根目录 [`SKILL.md`](../SKILL.md) 是总入口。用户选择 `00` 至 `05` 或“全部”后，分别执行对应的
[`skills/`](../skills/) 子 Skill。未选择前只展示清单，不修改用户级文件。

## 获取同一份仓库快照

1. 对 GitHub 链接，优先解析用户指定的 ref；只有仓库地址时解析默认分支当前 commit，再使用该 commit 的公开 HTTPS
   归档或原始文件。无需登录 GitHub，也不要求安装 Git。若 REST API 限流，可用公开归档；不要为解决限流索要 Token。
2. 必须先完整读取根 `SKILL.md`、锁文件和本规则，再读取被选中的子入口。仅把仓库 URL 传给普通 Skill 安装器不能执行这里的路由。
3. 能解析 commit 时，所有本仓库文件都从该 commit 获取。无法解析时可以使用一次下载的完整归档作为快照，记录归档
   SHA-256 和“commit 未验证”；不能再从移动中的分支单独补文件。归档缺失文件时重新获取完整快照或报告失败。
4. 对本地目录，读取其工作区内容，记录可用的 HEAD 和 dirty 状态；脏工作区不能冒充该 HEAD 的原始内容，可记录文件清单和哈希。
5. 外部仓库必须使用锁定 commit。完整复制所选 Skill 目录，包括 `agents/`、references、模板和脚本；复制不代表运行这些脚本。

## 新设备预检（所有子入口共用）

### 配置目录与 Skill 目录

- `<CodexHome>`：当前进程明确设置的 `CODEX_HOME`，否则为用户目录下 `.codex`。这里只存配置、全局规则和安装备份。
- `<SkillRoot>`：单独确定当前客户端实际扫描的用户级 Skill 目录。优先使用本机已加载的**用户安装 Skill**路径、
  客户端明确给出的发现路径或对应版本文档；不要把系统技能目录、插件缓存或项目级目录当作用户级目录。
- 全新设备没有已加载用户技能或明确路径时，按当前官方文档使用用户目录下 `.agents/skills`；较旧客户端明确使用
  `<CodexHome>/skills` 时沿用其路径。目录存在、安装器默认值或 `CODEX_HOME` 本身不能单独证明客户端会扫描该目录。
- 用户指定目标目录时沿用，但发现路径不匹配应报告 `unverified`，而不是宣称加载成功。安装器支持目标参数时必须传入
  已解析的 `<SkillRoot>`；同一次安装只选择一个目标目录，不向两个候选位置重复安装。
- 先检查选定目录、其他已知扫描位置和已加载技能的同名 `name`。跨目录重复也列为冲突；不静默搬迁或删除已有 Skill。

当前官方目录和发现规则参考 [Skills 文档](https://developers.openai.com/codex/skills)。文档与本机客户端证据不一致时，
说明依据并以实际客户端证据为准；仍不能确定时使用文档路径并保留待新会话验证状态。

### 有效全局规则

读取 `<CodexHome>/AGENTS.md` 和 `AGENTS.override.md`。后者存在时按当前客户端规则检查其是否遮蔽 `AGENTS.md`，
不得仅因基础文件已写入就声称规则生效。安装 `01` 的 Matt Pocock 建议区块时，绝不修改、删除、改名或复制到
`AGENTS.override.md`；只在用户确认后合并到基础 `AGENTS.md`，若 override 遮蔽基础文件则把该区块的生效状态标为
`blocked`。其他懒人包已有的 override 合并规则仍按对应入口执行。
项目级规则也可能覆盖全局规则，因此全局规则生效不等于任意项目都会执行同一策略。
参见 [AGENTS.md 文档](https://developers.openai.com/codex/guides/agents-md)。

### `00` 的模型与配置

安装 `00` 前检查当前客户端、账户或工作区明确暴露的可用模型及推理等级，核对 `gpt-6-luna`、`gpt-6.1-sol` 和 `max`。
官方模型存在不代表本机账户可用；无需为了预检发起付费模型请求。可用性无法确认时也按未验证处理。
参见 [Codex 模型文档](https://developers.openai.com/codex/models)。

缺少模型、等级或客户端配置支持时，保留现有默认模型与可运行配置，不写入未验证的模型覆盖，也不启用依赖它们的
agent 配置；工作流 `AGENTS.md` 中绑定这些模型的路由指令也属于受影响内容，不能在模型检查失败时单独激活。
分别报告受影响文件为 `pending`；其余已选择安装包可以继续。用户明确要求其他可用模型时，展示新差异，
记录偏离锁定来源的配置，不静默替换模型。不安装或更新 Codex 客户端来绕过此检查。

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

选择 `01` 时，将第二套来源的以下 18 个目录安装到预检确定的 `<SkillRoot>`，并把懒人包自带的
[`global-skill-suggestion-section.md`](../skills/01-mattpocock-engineering/assets/global-skill-suggestion-section.md)
合并到 `<CodexHome>/AGENTS.md`，使工作对话能在强匹配时建议用户手动调用九个非自动调用 Skill：

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

选择“全部”时，按 `00`、`01`、`02`、`03`、`04`、`05` 的顺序执行。
`00` 更新基础 `AGENTS.md` 时必须保留其中所有格式有效的其他懒人包受管区块；随后 `01` 再单独合并自己的建议区块。

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

所有 Skill 共用预检确定的 `<SkillRoot>`，不要由各子入口或安装器重新猜测路径。

## 冲突处理

### 配置文件

1. 先读取现有文件并与固定 commit 中的文件比较。
2. 无差异则标记 `already-current`，不重复写入。
3. 有差异则把现有文件备份到 `<CodexHome>/lazy-pack/backups/<timestamp>/`，并展示差异。
4. 通过对话让用户选择：手动合并、使用上游版本、保留现有版本。
5. 手动合并完成后再次读取目标文件，确认写入结果；用户未确认时保持 `pending`。

不要为了合并 TOML 而猜测用户配置的语义；无法安全自动合并时，保留双方文件并让用户决定。

### `AGENTS.md` 受管区块

懒人包在基础 `<CodexHome>/AGENTS.md` 中分别维护第二大脑规则和 Matt Pocock 技能建议；每个区块只由自己的稳定标记包围。

第二大脑全局规则标记：

```text
<!-- codex-second-brain-managed:start -->
...
<!-- codex-second-brain-managed:end -->
```

Matt Pocock 技能建议区块标记：

```text
<!-- codex-lazy-pack-matt-skills-managed:start -->
...
<!-- codex-lazy-pack-matt-skills-managed:end -->
```

1. 合并 `01` 区块前，读取基础 `AGENTS.md` 与 `AGENTS.override.md`；即使 override 遮蔽基础文件，也不得把该建议规则写入 override。
2. 若目标区块内容相同则标记 `already-current`。否则先读取当前文件、备份整个已有 `AGENTS.md` 到
   `<CodexHome>/lazy-pack/backups/<timestamp>/`，展示只涉及该区块的新增、追加或替换差异，并等待用户确认；用户跳过时保留原文件，
   但仍可独立安装 18 个 Skill。
3. 起止标记都不存在时，在用户确认后把源区块追加到文件末尾；不要修改文件中其余用户规则或其他懒人包区块。
4. 起止标记恰好各出现一次且顺序正确时，只比较并原位更新该区块；其他区块及区块外内容逐字保留。
5. 标记残缺、顺序错误、嵌套或重复时停止自动修改，保留原文件并报告 `pending`；不尝试修补标记。
6. 新建、更新、跳过或无法合并都作为独立状态记录；若 `AGENTS.override.md` 当前遮蔽基础文件，建议区块报告 `blocked`（同时注明基础文件区块本身是否已安装）。
7. 安装或更新 `00` 的工作流 `AGENTS.md` 时，识别并保留所有格式有效的懒人包受管区块，包括
   `codex-second-brain-managed` 和 `codex-lazy-pack-matt-skills-managed`；遇到非本懒人包的成对标记区块也不得无故删除。
   执行“全部”时先安装 `00`，再由 `01` 合并建议区块，后续 `05` 再合并第二大脑区块。

### 同名 Skill

1. 比较目录中的文件和内容；相同则标记 `already-current`。
2. 不同则先展示新增、删除和修改的路径。
3. 用户选择替换时，先备份整个现有 Skill 目录。
4. 用户选择手动合并时，保留上游目录作为候选，并报告需要用户完成的合并；确认应用合并后同样先备份整个现有目录。
5. 用户选择跳过时不改变现有 Skill。

## 安装后报告

逐项独立报告以下三列，不把文件复制等同于运行成功：

| 维度 | 状态与依据 |
| --- | --- |
| 文件安装 | `installed`、`already-current`、`skipped`、`pending` 或 `failed`；重新读取目标并核对完整文件清单和内容 |
| 客户端发现 | `discovered`：客户端实际列出对应 name/路径或确认规则来源；`unverified`：待刷新/新会话；`blocked`：已确认路径、屏蔽或冲突问题 |
| 功能验证 | `verified`：实际执行了授权范围内的检查；`not-run`：未执行技能业务；`blocked`：已证实存在缺失依赖或运行错误 |

安装后使用客户端可提供的技能清单或发现诊断核对 name 和路径；不能通过自己直接读 `SKILL.md` 证明自动发现。
全局规则用有效来源列表核对；当前会话未刷新时标为 `unverified`，提示开启新会话再检查，不自动重启正在工作的客户端。
动态隐式调用、显式调用和业务操作分别看待；显式调用 Skill 可用不代表它应该自动触发。
安装阶段不运行技能业务，仅结构验证不能填 `verified` 的业务结论。Matt Pocock 的校验警告和依赖按
[兼容性说明](mattpocock-codex-compatibility.md)记录。

`01` 还要单独报告 Matt Pocock 建议区块的状态（`installed`、`already-current`、`skipped`、`pending` 或
`blocked`）、基础规则目标、备份位置，以及客户端是否以 `AGENTS.override.md` 遮蔽基础文件。此状态不与 18 个 Skill
的文件安装状态合并；九项上游 Skill 的隐式调用限制仍按原样保留，不能因为建议区块已安装就声称它们已能手动调用。

### 提供安装后验证提示词

本次实际执行了安装或更新时，最终回复前读取[安装后验证提示词](post-install-verification-prompt.md)，并将其完整作为独立代码块提供，方便用户直接复制到同一 Codex profile 的新对话。
说明新会话用于验证客户端发现和全局规则刷新；若新会话仍未发现已安装 Skill，再建议重启 Codex。仅展示清单、尚未安装时不需要提供。

安装完成后保存一份本机状态报告到 `<CodexHome>/lazy-pack/installations/<timestamp>.json`，记录包版本、快照身份、
选择编号、预检依据、目标路径、实际来源 commit、各维度状态、备份和待处理项；不保存凭证。此报告用于以后更新和核对，
不能代替重新读取文件或客户端发现检查。报告写入失败需说明，不把已经成功的文件安装改称失败。

至少报告：

- 实际执行的懒人包编号。
- 实际执行来源使用的 commit（只报告实际执行的来源）。
- `00` 的 4 个工作流文件、`01` 的 18 个 Skill，以及 `02` 至 `05` 的逐项状态。
- `01` 的 Matt Pocock 建议区块状态、目标 `AGENTS.md`、备份和 override 遮蔽情况；与 Skill 文件状态分开报告。
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
