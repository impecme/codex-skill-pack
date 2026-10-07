# codex-lazy-pack

> 给执行安装的 Codex：收到本仓库链接或目录后，先读取根目录 [`SKILL.md`](SKILL.md)、
> [`sources.lock.json`](sources.lock.json) 和[共享安装规则](references/conversation-install.md)，再按用户选择执行 `00`–`05`。
> 本仓库的根目录和 `skills/` 是安装入口；实际待安装内容由锁文件指定。请先解析入口，再调用具体 Skill 的安装能力。

这是我的个人 Codex 懒人包。它把常用工程工作流、代码工程和 GitHub/Obsidian Skill
固定到指定 commit，并在仓库内维护个人第二大脑 Skill。新机器上只需要把这个仓库交给大模型，通过对话即可选择并
完成用户级安装。第二大脑完成一次性配置后，会通过用户级全局规则自然融入项目工作，不需要手动提醒开工、记录或收工。

当前懒人包版本：`0.7.0`。个人第二大脑采用 Foam-inspired Schema 2；Vault schema 为 `2`，设备配置 schema 为 `2`。

本项目采用“总入口 + 独立懒人包”的组织方式：

- 总入口和选择路由：[`SKILL.md`](SKILL.md)
- 独立懒人包：`skills/<name>/SKILL.md`
- 上游版本锁定清单：[`sources.lock.json`](sources.lock.json)
- 共享安装规则：[`references/conversation-install.md`](references/conversation-install.md)
- 安装后验收：[`references/post-install-verification-prompt.md`](references/post-install-verification-prompt.md)

## 快速开始：通过对话安装

将本仓库链接或目录交给 Codex，并发送：

```text
请安装 https://github.com/impecme/codex-skill-pack 中的懒人包。
```

大模型应先读取 [`SKILL.md`](SKILL.md)，根据你的选择再读取对应的
`skills/<name>/SKILL.md` 和[对话式安装规则](references/conversation-install.md)，最后逐项安装并报告结果。

未指定编号时，Codex 先展示 `00`–`05` 供你选择；你也可以直接说“全部”。安装前会确认当前客户端的用户级 Skill
目录、有效全局规则文件，以及 `00` 所需模型是否可用。配置目录和 Skill 目录分别解析，不能只凭目录存在就判定能够加载。
本次仓库说明和内置资产来自同一份快照；外部来源继续固定到锁文件中的 commit。

完成报告会分别列出“文件安装状态”“Codex 发现状态”和“功能验证状态”。新会话才能完成的检查会标记为待验证；
安装时不执行 GitHub 登录、Vault 写入等技能业务操作。Matt Pocock 的隐式调用限制、全局建议区块和缺失依赖按
[兼容性说明](references/mattpocock-codex-compatibility.md)检查。

安装完成后，Codex 还会提供一份[独立的安装后验证提示词](references/post-install-verification-prompt.md)，供你复制到同一
Codex profile 的新对话中验收文件安装、客户端发现和只读功能测试。

## 可用懒人包

| 编号 | 名称 | 内容 |
| --- | --- | --- |
| `00` | `codex-sol-luna-workflow` | Luna/Sol 工程工作流配置、`AGENTS.md` 和两个 agent 配置 |
| `01` | `codex-mattpocock-engineering` | `mattpocock/skills` Engineering 目录的 18 项技能，以及对九项非自动调用 Skill 的全局建议规则 |
| `02` | `codex-github` | GitHub CLI、Git 配置和 GitHub 访问工作流 |
| `03` | `codex-obsidian` | Obsidian Vault 授权、MCPVault 和读写验证工作流 |
| `04` | `codex-github-obsidian` | GitHub 与 Obsidian 的联动工作流 |
| `05` | `codex-second-brain` | 第二大脑 Skill，以及自动融入项目工作的全局规则 |
| `全部` | — | 依次安装 `00` 至 `05` |

对应入口：

- [00：Luna/Sol 工程工作流](skills/00-sol-luna-workflow/SKILL.md)
- [01：Matt Pocock Engineering 技能](skills/01-mattpocock-engineering/SKILL.md)
- [02：GitHub](skills/02-github/SKILL.md)
- [03：Obsidian](skills/03-obsidian/SKILL.md)
- [04：GitHub + Obsidian](skills/04-github-obsidian/SKILL.md)
- [05：第二大脑](skills/05-second-brain/SKILL.md)

## 00：Luna/Sol 工程工作流

来源：[impecme/sol-luna-engineering-workflow](https://github.com/impecme/sol-luna-engineering-workflow)

该来源是基于官方仓库 [BruceLanLan/sol-luna-engineering-workflow](https://github.com/BruceLanLan/sol-luna-engineering-workflow) 的个人 fork。

锁定 commit：`ada4058bfa2f6a7c718c72d7c2b9c555eb3eea38`

模型配置：默认使用 `gpt-6-luna` + `max`；困难判断使用 `gpt-6.1-sol` + `max`。

安装到用户级 Codex 目录（通常是 `~/.codex`）：

- `AGENTS.md`
- `config.toml`
- `agents/luna-worker.toml`
- `agents/sol-advisor.toml`

上游 README、文档和贡献指南不会被复制到用户配置目录。

## 01：Matt Pocock Engineering 技能

来源：[mattpocock/skills Engineering](https://github.com/mattpocock/skills/tree/main/skills/engineering)

锁定 commit：`3cca18b368ae95cdbdebbff572ccafa662551015`

选择 `01` 或“全部”时，18 项都会安装到用户级 Skill 目录：

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

同时，`01` 会按确认流程把[全局建议规则](skills/01-mattpocock-engineering/assets/global-skill-suggestion-section.md)合并到用户级
`<CodexHome>/AGENTS.md`。它会在具体工作与某项 Skill 高度匹配时推荐一项手动调用并等待你选择；拒绝后照常继续，不会自动启动 Skill。
规则只修改自己的受管区块，保留其他全局内容；若 `AGENTS.override.md` 遮蔽基础文件，不修改 override，并把有效状态报告为 `blocked`。
上游九项 Skill 的自动调用限制保持原样，手动调用菜单是否可用仍按当前客户端单独验证。

## 02–04：GitHub 与 Obsidian 相关 Skill

这三项来自 [mathruffian-dot/codex-lazy-packs](https://github.com/mathruffian-dot/codex-lazy-packs)，
固定在 `574818e2d80b31807b74fcf62dd5b90b9e46ef3f`：

- `02` 安装 `codex-github`，用于检查 Git、GitHub CLI、GitHub 登录状态和后续 GitHub 工作流。
- `03` 安装 `codex-obsidian`，用于选择 Vault 授权方式、配置可选的 MCPVault，并验证读写。
- `04` 安装 `codex-github-obsidian`，用于执行 GitHub 与 Obsidian 的组合工作流。

这里的“安装”只把固定版本的 Skill 放入用户级 Skill 目录，不会在懒人包安装阶段自动登录
GitHub、修改全局 Git 配置、创建或推送仓库、写入 Obsidian Vault，也不会自动保存凭证。
安装完成后，再通过对话触发相应的已安装 Skill。

## 05：个人第二大脑（Foam-inspired Schema 2）

`05` 安装本仓库维护的 [`codex-second-brain`](bundled-skills/codex-second-brain/SKILL.md)，
不再使用参考仓库中的简版三层结构 Skill。它还会把
[`global-agents-section.md`](bundled-skills/codex-second-brain/assets/global-agents-section.md) 作为受管区块合并到
用户级 `<CodexHome>/AGENTS.md`，使 Skill 不依赖用户每次显式触发。

该内置 Skill 的指令、生成模板和默认笔记内容均使用简体中文；机器字段、模式标识和
ASCII 路径保持英文，以保证跨设备兼容性和升级稳定性。它坚持一个 Vault，不为每个项目建立独立事实源：

- 设备之间只用 Syncthing 同步同一个主 Vault；GitHub 私有仓库只由指定设备人工 commit/push，作为备份和历史审查，不承担实时同步。
- 项目使用 `index.md` 保存身份和导航，`status.md` 保存生命周期、当前目标、进度、阻塞和下一步；经验拆成 `lessons/` 下的原子笔记，避免一个不断膨胀的 lessons 文件。
- 长期知识按 `30-Knowledge/<topic>/` 组织，每个主题有自己的 `index.md`，主题笔记保持单主题、可独立引用。
- 每个受管笔记都有不可变的“类型前缀 + UUIDv4”身份；`project_id` 继续表示规范化仓库映射，不与笔记 UUID 混用。
- 内部链接使用 Vault 根相对、路径限定的 Wikilink（例如 `[[10-Projects/<project-id>/status|项目状态]]`），不带前导 `/` 或 `.md`，不依赖可能产生歧义的全库同名链接。
- Skill 随包提供 16 个模板和 Schema 2 资产；初始化后，Vault 内 `90-System/templates/` 是模板权威，`90-System/schemas/schema-v2.md` 与系统清单记录当前约定，Skill 目录中的资产只用于 bootstrap、repair 或 fallback。
- `setup`、`link`、`startup`、`checkpoint`、`shutdown`、`weekly`、`promote` 和 `repair` 是内部动作，不是用户操作清单。

Schema 2 的稳定目录骨架如下：

```text
<Vault>/
├─ index.md
├─ 00-Inbox/
│  ├─ <year>/<month>/<timestamp>-<device-short>-<slug>.md
│  └─ weekly-review-<year>-W<week>-<device-short>.md
├─ 10-Projects/
│  ├─ index.md
│  └─ <project-id>/
│     ├─ index.md
│     ├─ status.md
│     ├─ sessions/<year>/<timestamp>-<device-short>-<id8>.md
│     ├─ decisions/<decision-id>-<slug>.md
│     ├─ experiments/<experiment-id>-<slug>.md
│     └─ lessons/<lesson-id>-<slug>.md
├─ 20-Areas/
│  ├─ index.md
│  └─ <area-id>/index.md
├─ 30-Knowledge/
│  ├─ index.md
│  └─ <topic-id>/
│     ├─ index.md
│     └─ <knowledge-id>-<slug>.md
├─ 40-Resources/
│  ├─ index.md
│  └─ <web|paper|book|repository|other>/<resource-id>-<slug>.md
├─ 50-Daily/
│  └─ <year>/<YYYY-MM-DD>.md
├─ 60-Archive/
├─ 90-System/
│  ├─ second-brain.md
│  ├─ schemas/schema-v2.md
│  └─ templates/
└─ attachments/
```

安装 `05` 只把 Skill 安装到用户级目录，并把全局规则合并到 `<CodexHome>/AGENTS.md`；不会定位、创建或修改真实 Vault，
不会写设备配置，也不会配置 Syncthing、GitHub 备份、定时任务或执行迁移。已有 Schema 1 Vault 以后必须在用户明确确认后，
通过 `repair` 的 Schema 1→2 子动作显式迁移。安装阶段不代办这一步。

`05` 不安装 Foam、`foam-cli`、VS Code 扩展或任何 MCP，也不增加本地一键脚本；本次 Schema 2 变化不改变 `00`–`04`。
完整方案见[第二大脑更新方案](references/second-brain-update-options.md)和
[开源第二大脑组织形式调研](references/open-source-second-brain-organization-research.md)。

### 第二大脑如何融入日常任务

普通项目任务的外部体验仍然是“提出任务 → Codex 完成任务 → 获得结果”。内部按需发生：

```text
首次处理当前项目任务：静默读取项目 index、status 和最近 Session
实际开发、调试、测试、研究或评审：优先完成项目工作
产生持久成果：写入当前任务唯一的设备独立 Session
最终回复前：补全结果、证据、阻塞和下一步
```

不会为每个命令、工具调用或对话轮次写笔记，也不会把同一正文复制到 Daily、Session、status、lessons 和 Knowledge。
普通问答或没有持久结果的检查不写入。只有首次建库、首次关联项目、共享状态或正式知识修改、冲突处理、移动删除
以及 Git commit/push 等必要动作才会要求确认。

## 对话式安装行为

- 用户未选择编号时只展示清单，不直接修改用户级配置。
- 大模型直接使用可用的 Codex Skill、文件和仓库工具完成安装。
- 外部上游内容按 `sources.lock.json` 中的 commit 获取；内置第二大脑 Skill 按懒人包版本和仓库 commit 追踪。
- 不执行本地一键安装脚本；懒人包安装过程不使用 `npx`、不要求 Node.js、`uv`、Git 或 GitHub CLI。
- GitHub/Obsidian Skill 后续可能会检查或引导这些工具，但那属于主动使用 Skill 的下一步。
- 不在安装过程中要求 GitHub 登录或自动配置凭证。
- `05` 安装阶段不定位真实 Vault、不执行 Schema 迁移；Schema 1 到 Schema 2 只能由用户确认后的 `repair` 迁移子动作完成。
- 配置或同名 Skill 冲突时，先展示差异并询问用户。
- `05` 使用稳定注释标记原位维护 `AGENTS.md` 区块；不得覆盖其他全局规则或追加重复区块。
- 安装完成后提示是否需要重启 Codex，以便刷新新 Skill。

## 冲突、备份和恢复

已有文件不会被静默覆盖。发生冲突时，大模型应：

1. 显示当前文件与上游文件的差异。
2. 对替换或手动合并的内容先备份到 `<CodexHome>/lazy-pack/backups/<时间戳>`。
3. 通过对话让用户选择替换、跳过或手动合并。
4. 未完成的手动合并保留为 `pending`，并在最终报告中说明。

重复安装时，同一 commit 且内容相同的配置或技能会直接标记为 `already-current`；不同来源或已被修改的同名内容会再次进入冲突流程。

## 个人开发中的推荐用法

安装后，可以把这些技能组合成通用开发闭环：

1. `codex-second-brain` 在外围自动恢复当前项目上下文。
2. 用 `grill-with-docs` / `to-spec` 固化目标、约束和验收标准。
3. 用 `prototype` 验证不确定的设计或建立 baseline。
4. 用 `implement` / `tdd` 开发，并保持测试和检查可重复执行。
5. 用 `diagnosing-bugs` 根据证据排查错误和回归。
6. 用 `code-review` / `codebase-design` 检查实现质量和架构边界。
7. 用 `research` 查询需要的一手资料。
8. 在有持久结果的任务结束前，第二大脑自动保存一条简洁 Session；正式知识仍经复核后沉淀。

## 更新锁定版本

懒人包不会自动追踪上游最新版本。需要升级时，维护者应先修改
[`sources.lock.json`](sources.lock.json) 中的 commit，检查上游变更，再提交这个懒人包的版本更新。这样不同机器仍能复现同一套环境。

## 插件/MCP 扩展

`sources.lock.json` 已预留 `extensions.plugins` 和 `extensions.mcp` 数组。本次 Schema 2 / `05` 不安装 Foam、CLI、VS Code 扩展或 MCP，
也不会自动扫描或安装未确认的插件、MCP server 或凭证配置。本项目本身不作为 Codex 插件安装；`00`–`04` 的既有入口和行为不在本次变更范围内。

## 范围说明

当前版本封装三个外部固定来源类别：个人 fork 的 Luna/Sol 工作流、Matt Pocock Engineering 技能，
以及 mathruffian-dot 懒人包中的 GitHub/Obsidian Skill；个人第二大脑 Skill 由本仓库直接维护。
工作区中的本地资料不会自动复制；如需加入个人常用资料或 Skill，可以在后续版本新增独立的
`skills/<name>/SKILL.md` 和对应来源。
