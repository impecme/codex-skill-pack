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

安装 `00` 前检查当前客户端、账户或工作区明确暴露的可用模型及推理等级，核对 `gpt-6-luna` + `max` 与 `gpt-6.1-sol` + `high`。
官方模型存在不代表本机账户可用；无需为了预检发起付费模型请求。可用性无法确认时也按未验证处理。
参见 [Codex 模型文档](https://developers.openai.com/codex/models)。

缺少模型、等级或客户端配置支持时，保留现有默认模型与可运行配置，不写入未验证的模型覆盖，也不启用依赖它们的
agent 配置；工作流 `AGENTS.md` 中绑定这些模型的路由指令也属于受影响内容，不能在模型检查失败时单独激活。
分别报告受影响文件为 `pending`；其余已选择安装包可以继续。用户明确要求其他可用模型时，展示新差异，
记录偏离锁定来源的配置，不静默替换模型。不安装或更新 Codex 客户端来绕过此检查。

## 固定来源

- 工作流 fork：[impecme/sol-luna-engineering-workflow](https://github.com/impecme/sol-luna-engineering-workflow/tree/c1376779ada82ed540e052a74d23538c07f1a1e6)
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
`<CodexHome>/AGENTS.md`。随后依照
[`syncthing-bootstrap.md`](../bundled-skills/codex-second-brain/references/syncthing-bootstrap.md) 和
[`github-backup-bootstrap.md`](../bundled-skills/codex-second-brain/references/github-backup-bootstrap.md) 完成双机引导：每台设备都要在本机 Codex 环境执行一次 05，分别准备本机 Syncthing 与 Vault 路径，再由用户在两边对话间传递配对卡、接收就绪状态和 manifest 指纹。选择 05 授权本机准备；启用公共发现/relay、登记对端、首次内容传输、提升为双向模式、PC 端 Git 初始化或 GitHub 远端变更，必须按相应参考逐项说明并取得确认。路径缺失时集中询问；冲突时停止相关写入与阶段转换，但不撤销其他懒人包的已完成安装。

所有 Skill 共用预检确定的 `<SkillRoot>`，不要由各子入口或安装器重新猜测路径。

## 新版优先更新与归属边界

“新版”指本次读取的同一仓库快照及 `sources.lock.json` 中锁定的来源 commit，不是安装过程中追踪上游分支。用户再次要求安装已安装过的懒人包时，先检查安装记录并按**更新**处理，不重复执行首次配置。

用户已授权新版优先：已确认归属于本次所选懒人包的受管内容有差异时，先备份并核验，再自动替换为锁定版本；无需逐文件请求“替换/跳过/合并”。受管内容上的本地修改也会被新版替换，并在报告中注明。此授权不扩大到未知来源同名内容、混合文件中的非受管内容或第二大脑运行数据。

### 归属判定

按以下证据由强到弱确认旧安装归属：

1. `<CodexHome>/lazy-pack/installations/` 中记录了对应 pack、来源 ID/commit、目标路径及交付文件清单，且该单元上次状态为 `installed`、`already-current` 或 `updated`；`skipped`、`pending`、`failed` 不证明归属。文件内容后来被改动不取消该路径的受管归属。
2. 完整、唯一、顺序正确的受管区块标记，确认该区块归标记 ID 对应的 pack 所有。
3. 旧版没有文件清单时，根据旧安装报告中的来源 commit 读取当时的锁定源目录/文件清单；必要时将本地内容与该可信旧快照比对。只匹配 `SKILL.md` 不足以证明整个目录都属于 pack。
4. 没有上述证据时，目标路径、文件名、Skill 名称、内容相似或“新版本也要写到这里”都不能单独证明旧内容归属。报告具体冲突并一次性询问是否接管该范围；用户确认后记录接管范围，未来更新无需重复询问。

来源记录互相矛盾、目标路径不唯一、跨扫描目录出现同名 Skill、检测到符号链接/junction 将目标引出预期目录、或新来源不完整/未锁定时，只阻断受影响单元，不写入该单元；其他独立所选 pack 可继续。

### 备份与应用

1. 先完整读取并校验锁定来源、目标及所有权证据；按文件或独立受管区块比较，报告新增、修改、删除和“本地修改将被新版替换”的路径。
2. 每次更新使用唯一运行编号，备份到 `<CodexHome>/lazy-pack/backups/<timestamp>-<run-id>/`。备份放在 Skill 扫描目录和 Vault 之外。整目录备份 Skill；混合配置和受管区块更新备份整个原文件。备份清单记录原路径、源 ID/commit、归属依据、相对文件清单、SHA-256、拟变更及恢复映射；对备份回读核验后才能写入。
3. 写入前重新检查目标未变化；变化、备份失败或无法验证时停止该单元。写入后重新读取并验证目标与锁定来源一致，记录新文件清单和 SHA-256。绝不为覆盖方便删除整个 CodexHome、SkillRoot、Vault 或未知目录。

### 各类受管内容

- **Skill 目录：** 初装时记录完整相对文件清单及来源 commit。更新只替换旧清单中已确认受管的文件；旧版本明确交付但新版删除的文件才可删除。目录中的未知附加文件予以保留并报告；若它与新版新增目标重名，或无法确定旧清单，暂停该 Skill 目录并询问是否接管。只有目录全部内容均在可信旧清单中时才可整目录替换。
- **完整配置文件：** 仅当安装记录确认整文件受管，或旧文件与可信旧版来源精确相符时，才备份后自动整文件更新。文件名和映射目标本身不等于所有权。
- **混合 TOML：** 按 `sources.lock.json` 明确列出的精确键路径更新。已由旧安装记录确认受管的键，以新版值为准；未归属的其他键、table、注释和用户配置保留。新出现但没有旧归属证据的冲突键、重复键、解析错误或键所有权交叉时停止该配置文件写入，不猜测语义。00 的模型/agent 相关键作为一组校验，模型不可用或配置不兼容时不得启用该组。
- **`AGENTS.md`：** `01`、`05` 及 `00` 的受管区块只原位更新自身标记范围，其他 pack 区块和区块外正文逐字保留。完整有效的区块无需用户确认即可更新；缺少区块时，只有安装记录证明本次所选 pack 尚未安装该区块，才可自动追加。旧版 `00` 尚无标记时，只有能从可信旧来源唯一识别完整工作流文本范围，且移除其他有效 pack 区块后无未归属正文，才可迁移为新版标记区块；否则询问一次边界/接管范围。标记残缺、重复、嵌套或顺序错误时停止对整份文件的自动修改。
- **安装记录：** 每次成功后写入来源 commit、目标路径、归属类型/标记或 TOML 键、相对文件清单及 SHA-256、每个单元结果和备份位置。报告不保存凭证。旧版记录缺少清单时，用记录中的旧来源 commit 重建旧清单，不把当前新版清单倒推成旧版所有权。

### 第二大脑更新边界

- `<SkillRoot>/codex-second-brain/` 下已确认归属的 Skill 指令、脚本和内置 assets 可按受管 Skill 规则更新。
- `<CodexHome>/AGENTS.md` 中第二大脑标记区块仅在标记有效时原位更新，且必须保留暂停门槛。
- `<CodexHome>/second-brain/config.json`、`sync-onboarding.json`、Syncthing 配置/profile、设备身份与对端、folder 模式、服务状态、`.stignore`、Vault 内容/模板及 `.git` 均不是懒人包受管文件，更新时不得覆盖、删除、迁移或重置。
- 若本次是更新已有安装，只更新 Skill 文件和被证明归属的全局规则；不得重跑首次配置，不调用会改变状态的 `begin`、`apply`、`pair`、`start`、`promote` 或 `complete`，不得启动/暂停/重启既有同步。现有 `status`、`pendingOperation`、配对和传输状态原样保留并只读报告。连接设备、传输 Vault 内容、Git 操作和 Schema 迁移仍需各自授权。

### `AGENTS.md` 受管区块

懒人包在 `<CodexHome>/AGENTS.md` 中分别维护 Luna/Sol 工作流、第二大脑规则和 Matt Pocock 技能建议；每个区块只由自己的稳定标记包围。00 的新来源文本也必须由锁文件定义的标记包围。

Luna/Sol 工作流标记：

```text
<!-- codex-sol-luna-workflow-managed:start -->
...
<!-- codex-sol-luna-workflow-managed:end -->
```

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

1. 每次修改前读取基础 `AGENTS.md` 与 `AGENTS.override.md`，并检查所有懒人包标记。`01` 默认只写基础 `AGENTS.md`；若上次安装报告记录用户曾确认的其他目标，只在该相同目标和标记范围内更新，不擅自迁移到 `override`。
2. 对 `00`、`01`、`05`，各自标记完整、唯一、顺序正确且无嵌套，并有旧安装记录/受信来源证明归属时，先备份整个原 `AGENTS.md`，再自动原位替换该区块为锁定新版。其他 pack 区块与区块外正文逐字保留，无需逐次确认。
3. 两个标记均不存在时：若报告证明该 pack 的区块原先已安装，则视为受管内容被移除，备份后恢复新版；若是首次添加区块，仍按对应子 Skill 的原有确认边界，先展示差异并取得一次确认后追加。已有疑似旧规则但无法确认边界时，只询问一次是否接管该具体文本范围。
4. 旧版 `00` 工作流文本没有标记时，读取安装报告中的旧来源 commit，获取可信旧 `AGENTS.md`；移除其他格式有效的懒人包区块后，只有剩余文本与旧来源完整一致，才自动迁移成标记区块并更新。存在额外未归属正文时保留并询问一次边界，不覆盖整份文件。
5. 起止标记残缺、顺序错误、嵌套或重复，或多个 pack 声明同一区块时，停止对该文件的全部自动写入并报告 `pending`；不猜测修补。
6. `AGENTS.override.md` 遮蔽基础文件时单独报告有效规则目标；不得因安装更新自行改写 override。只对安装报告中已获用户确认的 override 受管区块原位更新。更新规则不改变首次安装时新增全局区块需取得确认的既有边界。
7. 执行“全部”时仍按 `00`、`01`、其余来源、`05` 顺序处理；每个 pack 只写自身区块，某一边界问题不影响其他可独立安装项。

### 同名 Skill

1. 以旧安装报告中的来源 commit 与文件清单确认目录内各文件的归属；没有清单时，用旧 commit 重建来源文件清单。受管文件即使被本地修改，仍以锁定新版为准。
2. 对受管文件展示新增、修改、删除路径，备份整个原 Skill 目录并核验后，自动更新受管路径。只删除可信旧清单中由该 pack 交付、且新版已移除的文件；保留未知附加文件。
3. 新版新增文件若与未归属的现有文件碰撞、来源不同、旧清单无法重建或整目录所有权不完整时，暂停该 Skill 并询问一次具体接管范围；不能因同名目录就清空重建。
4. 跨扫描目录存在另一份同名 Skill 时，不自动搬迁、删除或接管另一份。路径、名称和相似内容不能单独证明来源。
5. 更新后重新读取并校验完整目标目录；记录实际受管文件清单及哈希。目标若已与本次锁定来源一致则标记 `already-current`，发生替换则标记 `updated`。

## 安装后报告

逐项独立报告以下三列，不把文件复制等同于运行成功：

| 维度 | 状态与依据 |
| --- | --- |
| 文件安装 | `installed`、`already-current`、`updated`、`preserved-unowned`、`skipped`、`pending` 或 `failed`；重新读取目标并核对受管文件清单/键/区块和内容 |
| 客户端发现 | `discovered`：客户端实际列出对应 name/路径或确认规则来源；`unverified`：待刷新/新会话；`blocked`：已确认路径、屏蔽或冲突问题 |
| 功能验证 | `verified`：实际执行了授权范围内的检查；`not-run`：未执行技能业务；`blocked`：已证实存在缺失依赖或运行错误 |

安装后使用客户端可提供的技能清单或发现诊断核对 name 和路径；不能通过自己直接读 `SKILL.md` 证明自动发现。
全局规则用有效来源列表核对；当前会话未刷新时标为 `unverified`，提示开启新会话再检查，不自动重启正在工作的客户端。
动态隐式调用、显式调用和业务操作分别看待；显式调用 Skill 可用不代表它应该自动触发。
安装阶段不运行技能业务，仅结构验证不能填 `verified` 的业务结论。Matt Pocock 的校验警告和依赖按
[兼容性说明](mattpocock-codex-compatibility.md)记录。

`01` 还要单独报告 Matt Pocock 建议区块的状态（`installed`、`already-current`、`updated`、`skipped`、`pending` 或
`blocked`）、基础规则目标、备份位置，以及客户端是否以 `AGENTS.override.md` 遮蔽基础文件。此状态不与 18 个 Skill
的文件安装状态合并；九项上游 Skill 的隐式调用限制仍按原样保留，不能因为建议区块已安装就声称它们已能手动调用。

### 提供安装后验证提示词

本次实际执行了安装或更新时，最终回复前读取[安装后验证提示词](post-install-verification-prompt.md)，并将其完整作为独立代码块提供，方便用户直接复制到同一 Codex profile 的新对话。
说明新会话用于验证客户端发现和全局规则刷新；若新会话仍未发现已安装 Skill，再建议重启 Codex。仅展示清单、尚未安装时不需要提供。

安装完成后保存一份本机状态报告到 `<CodexHome>/lazy-pack/installations/<timestamp>.json`，记录包版本、快照身份、
选择编号、预检依据、目标路径、实际来源 commit、各维度状态、所有权证据、各受管单元/Skill 的相对文件清单与 SHA-256、
TOML 键或 managed-section 标记、备份位置及恢复映射、更新前后结果和待处理项；不保存凭证、Vault 正文或设备密钥。
此报告用于以后重建旧版本的受管范围，不能代替重新读取目标或客户端发现检查。报告写入失败需说明，不把已经成功的文件安装改称失败。

至少报告：

- 实际执行的懒人包编号。
- 实际执行来源使用的 commit（只报告实际执行的来源）。
- `00` 的 4 个工作流文件、`01` 的 18 个 Skill，以及 `02` 至 `05` 的逐项状态。
- `01` 的 Matt Pocock 建议区块状态、目标 `AGENTS.md`、备份和 override 遮蔽情况；与 Skill 文件状态分开报告。
- 用户级 Codex 目录和 Skill 目录。
- 每个单元的归属依据、备份目录、被新版替换的本地修改、保留的未知文件、待处理冲突和需要重启 Codex 的提示。
- 未执行的插件/MCP/凭证配置。

对于 `02` 至 `04`，还要报告目标 Skill 目录、源目录、固定 commit、是否发生备份、
是否需要重启 Codex，以及安装阶段明确未执行的 GitHub 登录、push、MCP 配置和 Vault 写入。
对于 `05`，分别报告 PC 与服务器的 Skill 文件、全局规则、本机设备配置、Syncthing 程序/profile、Vault 文件夹、忽略规则、用户登录启动项和后台进程状态；首次安装按真实进度报告各配置阶段。更新分支只读检查，不推进阶段；报告实际观察到的配对/连接、传输、idle/needs/errors、manifest、GitHub 私有远端状态、`pendingOperation` 和未完成步骤，并注明配置未被本次更新改动。不得笼统声称“未添加远端”或“未传输”，而应报告实际观测状态；真实跨设备同步未验证时必须明确说明。只有对应阶段的本机 API 与跨设备证据均满足参考要求，才标记该阶段完成。

安装阶段不运行已复制 Skill 的正文指令；但 `05` 子入口可调用其内置本机同步/配对辅助程序，范围限于
[`syncthing-bootstrap.md`](../bundled-skills/codex-second-brain/references/syncthing-bootstrap.md) 与
[`github-backup-bootstrap.md`](../bundled-skills/codex-second-brain/references/github-backup-bootstrap.md)。`02` 至 `04` 之后由用户主动触发；`05` 完成并核验引导后由全局规则
在普通项目工作中自动调用。所有已安装 Skill 仍需遵守各自确认边界；尤其不能把 token、密码或其他凭证写入仓库、
`AGENTS.md` 或笔记。
