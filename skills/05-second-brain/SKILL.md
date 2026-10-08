---
name: codex-second-brain-pack
description: 安装并配置个人第二大脑，在 Windows 主电脑与 SSH Linux 服务器之间建立受控 Syncthing 同步，并配置 PC 端人工 GitHub 备份。
---

# 第二大脑 Skill 安装包

仅在用户选择 `05` 或“全部”时执行本 Skill。

## 目标

把本仓库内置的 Schema 2 `codex-second-brain` 安装到用户级 Skill 目录，合并自然维护规则，配置 Windows 主电脑和 SSH Linux 服务器各自的 Syncthing，并引导完成配对、首次单向播种、内容核验和双向同步启用。个人电脑是唯一主 Vault 与 GitHub 人工备份设备；服务器只保存同一 Vault 的镜像。

用户选择 `05` 即授权 Codex 在当前设备执行本 Skill 所列的本机安装与增量配置。涉及选定 Vault 路径、初始化知识库、启用公共发现/relay、开始首次文件传输、切换双向模式、初始化 Git 或设置 GitHub 远端时，仍须先说明精确影响并取得对应确认。需要另一台设备的 Syncthing Device ID 或状态时，由 Codex 生成配对卡/状态摘要并引导用户在两个 Codex 对话间传递；不索取 SSH 密码或私钥。未完成互联时报告待处理步骤，不阻断普通项目工程工作。

配置完成后，普通项目工作会自动恢复上下文、记录有持久价值的结果并在任务结束前收尾，不要求用户手动提醒内部模式。已有 Schema 1 配置或 Vault 不在安装阶段迁移；以后只能由 `repair` 的 Schema 1→2 子动作，在展示差异并获得明确确认后迁移。

## 固定来源

先读取仓库根目录的 `sources.lock.json`，只使用 `bundled-codex-second-brain` 条目：

- 本仓库源目录：`bundled-skills/codex-second-brain`
- 全局规则源文件：`bundled-skills/codex-second-brain/assets/global-agents-section.md`
- Vault schema 资产：`bundled-skills/codex-second-brain/assets/vault-schemas/`
- Vault 模板资产：`bundled-skills/codex-second-brain/assets/vault-templates/`（应有 16 个模板）
- Vault schema 和设备配置 schema：以 `sources.lock.json` 为准
- 目标目录：`<SkillRoot>/codex-second-brain`
- 全局规则目标：`<CodexHome>/AGENTS.md` 中 `codex-second-brain-managed` 标记包围的受管区块

先读取并执行[共享安装规则](../../references/conversation-install.md)的新设备预检，以其确定的 `<SkillRoot>` 为目标。
检查有效全局规则是否受 `AGENTS.override.md` 遮蔽并记录实际规则目标。下文 `<CodexHome>/AGENTS.md` 是默认目标；首次安装若用户要求写入有效 override，仍须先确认。更新时只在旧安装报告记录了用户确认的同一 override 目标和受管区块时原位更新；否则不改 override。

## 已安装版本更新与首次配置分流

先读取 `<CodexHome>/lazy-pack/installations/` 中的报告；若报告、可信旧来源或有效受管区块表明 `05` 已安装，本次按**更新**处理，即使用户口头说“安装”或选择“全部”。受管目录有差异时依共享规则备份并自动更新 `codex-second-brain` Skill；合法的 `codex-second-brain-managed` 区块有差异时备份整个目标文件并原位更新。

更新分支只更新已确认归属的 Skill 文件和全局规则，并只读报告现有第二大脑状态；不执行下方“双设备同步与第二大脑配置”中的首次安装步骤，不调用 `setup_syncthing.py` 或 `syncthing_pairing.py` 的 `begin`、`apply`、`pair`、`arm-receiver`、`start-source`、`promote-server`、`promote-primary`、`complete` 等操作，也不暂停、启动、停止、重启 Syncthing。不得改写设备配置、同步引导状态、Vault、`.stignore`、Git 元数据或设备/对端身份。若本次同时希望恢复或继续双机引导，先完成更新，再单独按相应阶段说明并请求确认。

安装记录缺失时，按共享规则用旧报告中的来源 commit 重建清单；归属或旧文本边界无法证明时只询问一次具体接管范围。更新完成后记录受管文件清单、哈希和备份位置；不能把更新 Skill 文件描述成第二大脑或跨设备同步已配置。

## 双设备同步与第二大脑配置

本节只在安装 `05` 时运行；日常项目工作和普通 `setup` 不自动重配同步。先完整阅读[双机引导](../../bundled-skills/codex-second-brain/references/syncthing-bootstrap.md)及[GitHub 人工备份引导](../../bundled-skills/codex-second-brain/references/github-backup-bootstrap.md)。所有辅助程序均由 Codex 在对话中调用，不要求用户手动运行脚本、打开 Syncthing GUI 或输入 Syncthing 命令。

完整双机配置需要在 PC 和 SSH Linux 服务器各自的 Codex 环境中安装/执行一次 `05`，使用相同懒人包快照。一个设备上的 Codex 无法替另一台设备写入它的本机配置或启动项；把这个边界说明给用户，并通过配对卡和状态摘要衔接两边对话。

1. **确定设备角色。** 当前设备只能是 `primary`（Windows 个人电脑）或 `server`（SSH Linux 服务器）。从设备配置、操作系统及用户回答交叉核对；不确定时询问，不猜测、不把服务器当主 Vault。
2. **检查并安装本机基础。** 读取 `sources.lock.json` 锁定的 Syncthing 版本/平台校验值，调用内置 `setup_syncthing.py preflight`。能安全推导的信息直接复用；缺失时一次询问当前 Vault 的绝对路径。PC 既有 Vault 沿用原路径；若需新建，默认建议在用户选定的父目录下使用 `第二大脑` 作为外层目录名，展示完整绝对路径并确认后才创建。服务器镜像路径必须独立确认，不能复用 PC 绝对路径；可建议相同的中文目录名，但其父路径由用户选择。服务器路径可不存在，但其父目录必须已存在，创建前展示完整路径并取得确认，目标必须为空。安装或更新不重命名既有 Vault；明确要求改名时作为独立迁移处理，先核对 Codex、Obsidian、Syncthing 两端等路径引用并停止相关写入/同步，不与首次安装混做。不得创建空 Vault 后假称内容已同步。
3. **处理本机冲突。** 只在 Syncthing 缺失时安装锁定官方版本并校验 SHA-256；已有版本不升/降级。写入前备份。未知远端、非目标活动文件夹、多个 profile、损坏/Schema 1 设备配置、路径或启动项冲突、服务器目标非空时，停止同步相关写入并说明恢复条件；其他已选 Skill 安装和普通工程工作可继续。
4. **先登记引导状态，再完成本机配置。** 在用户确认本机变更后调用 `setup_syncthing.py begin`，再读取它实际返回的 `status` 与 `maintenancePaused`；新引导应处于 `local-prepared`，已有阶段不得静默回退。随后调用 `setup_syncthing.py apply`。若状态已进入任一配对/播种/晋级阶段，或已是 `active`，辅助程序只读核对本机/已记录对端身份、固定 folder、路径、成员、阶段对应模式及网络安全基线，返回相应的 `existing-pair-no-changes`、`existing-pair-paused-no-changes`、`already-active-no-changes` 或 `active-sync-paused-no-changes`；不得暂停或重启同步、恢复首次安装网络默认值、改写 `.stignore` 或启动/停止服务。身份、路径、成员、模式或网络设置不符时停止本机同步配置并报告，不自动修复。仅尚未配对的新引导继续执行本机增量步骤：安全合并 `.stignore` 并保留用户规则；注册当前用户登录后台启动（SSH Linux 使用 systemd 用户服务并检查 linger）；监听和 GUI 限定 loopback、文件夹保持暂停、不自动打开浏览器。缺少 linger 时只给出需用户在服务器自行执行的管理员命令，不提权代办。验证本机 Syncthing Device ID、Vault 路径、忽略规则、启动项和运行状态。
5. **只在 PC 初始化主脑。** 对已有 Vault 先只读检查系统清单、Schema、目录布局和冲突：已声明或可明确识别的布局保持原样；混合、冲突或非空未知布局停止相关写入。仅全新空 Vault 默认采用 `schema2-zh-cn`；已有 Vault 即使缺少部分 Schema 2 结构，也沿用已确认布局。先展示目录/文件变更并确认，再用本 Skill 的 assets 初始化；将 schema 与模板中的 `{{PATH_*}}` 替换成该布局的真实路径，并在系统清单记录 `directory_layout`。保留 Obsidian 现有附件设置，不自动修改 `.obsidian` 或移动附件。服务器不初始化 Schema 2 笔记，只准备空镜像目录。Schema 1 不在安装中迁移。
6. **交换配对卡并配置网络。** 分别生成两端配对卡，卡片只包含设备标签、Syncthing Device ID、固定 folder ID、角色和连接/传输策略；严禁包含本地路径、第二大脑 `deviceId`、凭证或 SSH 私钥。引导用户在两台设备的 Codex 对话间人工传递并核对卡片。仅在说明公共设备发现/官方 relay 会处理 Device ID、IP 等连接元数据并获得确认后，才调用 `syncthing_pairing.py pair --confirmed-network-metadata` 启用发现/relay；只保留 loopback TCP 与官方动态 relay 地址，关闭 LAN 发现/公告和 Syncthing NAT/UPnP，不改路由器/防火墙。配对后验证两端 folder/peer 身份：PC `sendonly`、服务器 `receiveonly`，双方均保持暂停。需要重启使监听配置生效时，由辅助程序安全重启并重新验证；失败则报告部分进度与备份，不宣称配对完成。
7. **准备接收端，再开始首次传输。** 服务器收到 PC 配对卡后配对。服务器 Codex 只有在确认服务器目录仍为空、并取得用户对“解除服务器接收暂停”的明确确认后，才调用 `arm-receiver --confirmed-arm-receiver`，返回服务器 `receiveonly` 与唯一对端均已核验就绪的状态；由用户把该状态交给 PC 对话。PC Codex 只有在确认接收端就绪、两端 Obsidian/Codex/脚本及其他 Vault 写入者全部停写后，才可取得单独确认并调用 `start-source`。此前不得解除发送端暂停。用户若无法确认写入者已停止，就保持暂停。若操作中断，按 [同步中断恢复说明](../../bundled-skills/codex-second-brain/references/syncthing-bootstrap.md#中断恢复与安全边界)执行；不得直接重跑解除暂停操作。
8. **校验后分阶段开启双向。** PC 在停写期间生成 manifest SHA-256 并将指纹交给服务器。服务器必须核验唯一连接、receive-only、idle、无 needs/errors/receive-only 本地差异且本地 manifest 完全相等；用户再次确认两端应用写入者停写、PC 当前仍处于预期单向阶段并批准本阶段后，Codex 才调用 `promote-server`（带 `--confirmed-verified --confirmed-writers-paused --confirmed-peer-state`）。服务器晋级后仍停写，再把服务器最新状态和 manifest 交给 PC；PC 核验连接、idle、无待同步项/错误及指纹匹配，用户确认服务器已晋级、两端写入者停写且批准本阶段后，才调用 `promote-primary` 并带相同确认项。双方各自在本机调用 `complete`，提供对端最新 SHA-256 和核验结果；完成后状态才能变为 `active`。不得跳过任何阶段或用“目录存在”代替同步证明。双向写入探针会修改 Vault，除非用户另行授权，否则不执行并报告未验证。
9. **配置 PC 端 GitHub 人工备份。** 仅在 PC 上引导；Git/GitHub CLI 或认证缺失时说明由用户准备，不自动安装、不收集凭证。初始化 `.git`、创建/选择私有仓库和设置远端均先展示具体目标/差异并逐项确认。`.git` 必须由 `.stignore` 排除；不自动执行 `git add`、commit、push、pull 或周任务。服务器不初始化该 Vault 的 `.git`。
10. **报告完成度。** 分别报告每台设备本地配置、配对/连接、播种、双向同步、Vault Schema 2、PC GitHub 远端状态；清楚区分“已配置”“已验证”“待用户介入”和“未验证”。没有真实对端连接、内容 manifest 或网络证据时，不得声称已打通或已同步。`sync-onboarding.json` 非 `active` 或存在 `pendingOperation` 时，全局自动维护保持暂停，但不阻断无关项目工程工作。失败时只有本机身份、确切 folder、确切对端身份及两者暂停状态都回读核验，才可报告同步变更已停止；否则逐项报告失败/未知状态和待恢复操作。

## 执行要求

1. 读取内置源目录的全部文件，确认 `SKILL.md`、七个 Markdown reference（`data-model.md`、`github-backup-bootstrap.md`、`linking-and-health.md`、`migration-v1-to-v2.md`、`safety-and-sync.md`、`syncthing-bootstrap.md`、`workflows.md`）、`assets/vault-schemas/schema-v2.md`、
   `assets/vault-templates/` 下恰好 16 个模板、设备配置模板和全局规则资产完整可读。
2. 读取旧安装报告及可信旧来源清单。目录不存在时标记为待安装；内容相同则标记为 `already-current`。
3. 对已确认归本 Skill 管理的目录文件，展示新增、修改和删除路径，备份整个目标 Skill 目录并核验，然后自动更新到当前懒人包锁定版本；受管文件本地修改以新版为准。只删除旧清单证明由本 Skill 交付、且新版不再提供的文件，保留未知附加文件。
4. 新版新增路径与未知文件碰撞、来源不明、旧清单无法重建或目录含其他 Skill 内容时，只暂停该目录并询问一次具体接管范围；不能仅凭 `codex-second-brain` 同名目录清空重建。备份失败、路径不安全或目标在检查后变化时停止该单元。
5. 若本次是已安装版本更新，跳过双设备首次配置，只读保留设备和同步状态。仅首次安装时，才在本机 `setup_syncthing.py begin` 成功并核对实际状态后，将自然维护规则写入有效的 `<CodexHome>/AGENTS.md`；begin 冲突时不新增或启用该规则。
6. 单独检查 `<CodexHome>/AGENTS.md`：合法且归属已确认的受管区块有差异时，先备份整个文件再自动原位更新；其他 pack 区块及区块外正文逐字保留。缺少区块时按共享规则核验旧安装归属后恢复/追加。标记残缺、嵌套、重复或旧版文本边界不明时，停止该文件写入并报告 `pending`。
7. 写入后重新读取目标 Skill 和 `AGENTS.md`，验证 frontmatter、目录结构、全部 references 链接、
   schema 资产、16 个模板及 Schema 2 版本字段。设备配置模板先替换一组安全示例值再解析 JSON；不得要求未渲染占位符本身是合法 JSON。最后确认受管区块恰好出现一次且内容与源资产一致。
8. 从 `sources.lock.json` 记录当前懒人包版本、`vaultSchemaVersion` 和 `deviceConfigSchemaVersion` 及本次快照身份，
   按共享规则分别报告文件安装、客户端发现和功能验证状态；规则尚未刷新或被遮蔽不能标记为已生效。更新分支还需报告只读观察到的设备/同步阶段，不能宣称配置完成。
9. 仅首次安装时按“双设备同步与第二大脑配置”执行；首次播种前可检查/初始化经确认的 PC 主 Vault Schema 2 内容。更新分支不得重新初始化。不得迁移 Schema 1、跳过阶段确认、索取凭证、配置 MCP 或创建每周自动化。

### 安装阶段验证清单（不是 Vault 迁移）

- 七个 reference 和 schema 资产均可读取；模板必须精确包含 `root-index`、`collection-index`、`project-index`、
  `project-status`、`session`、`decision`、`experiment`、`lesson`、`area-index`、`topic-index`、`knowledge`、`resource`、
  `inbox-note`、`daily`、`weekly-review`、`system-manifest`。
- `sources.lock.json` 的包版本与内置源 `packageVersion` 必须一致，Vault schema 为 2，设备配置 schema 为 2；
  设备配置模板和 Vault schema 资产不得声明旧版本。
- 新建 Vault 选择 `schema2-zh-cn`，已存在的 ASCII 布局保留为 `schema2-ascii`；系统清单的 `directory_layout`、目录存在性、索引链接和模板路径必须一致。混合/歧义布局不得自动修复或创建第二套目录。
- schema 与模板中的所有 `{{PATH_*}}`、`{{DIRECTORY_LAYOUT_ID}}` 变量在实际写入 Vault 前必须替换；检查结果中不得残留未渲染变量。中文布局与 ASCII 兼容布局均须按同一逻辑目录映射验证。
- 每个模板必须声明 `schema_version: 2`、`id`、`title`、`type`、`created`、`updated`；`id` 占位符落盘前必须替换为对应类型前缀的 UUIDv4。
- 复制后的 Skill 与源目录逐文件一致，且其 references 链接、16 个模板和 schema 资产均存在。
- 仅首次配置时核对每台设备本机准备、配对、首次传输和分阶段晋级状态；已安装版本更新只读核验并保留原状态，不调用推进状态的辅助操作。配对等待阶段两端 folder 必须暂停；只有两端完成 `complete` 后才将该端状态标为 `active`。
- `<CodexHome>/AGENTS.md` 的 `codex-second-brain-managed` 起止标记恰好各出现一次，受管区块与源资产一致；其他全局规则保持不变。
- 安装仅访问用户确认的 Vault 路径；PC 首次初始化 Schema 2、服务器创建空镜像目录和开始首次传输均需对应确认。不得迁移 Schema 1；Schema 1→2 迁移必须稍后显式调用 `repair` 子动作并再次确认。

## 安全边界与报告

不要索要或保存 Vault 密码、API token、项目秘密或其他凭证。完成后报告懒人包版本、可用时的仓库 commit、
Skill 与全局规则的目标和状态、备份位置，以及是否需要重启 Codex。

全局规则只有在设备配置存在、Vault 可访问且同步引导状态文件不存在或为 `active` 时才执行自然维护；begin 成功至两端完成核验期间不读写 Vault。普通项目工程工作不会因此阻塞。首次建库和首次
项目关联仍需确认目标及变更；不能证明归本 Skill 管理的同名目录或文件不得自动接管。若检测到 Schema 1，只报告可迁移项，不得在安装阶段自动升级。
