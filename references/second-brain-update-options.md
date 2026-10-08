# 第二大脑更新方案与开源项目调研

> 调研日期：2026-10-02
> 场景：Windows、Codex、Obsidian、GitHub、个人开发工作流
> 资料原则：只引用官方文档、官方仓库和官方安全公告。项目状态为访问当日快照，引入懒人包时仍应锁定版本并重新验证。

## 结论先行

最适合当前懒人包的方案不是更换 Obsidian，也不是先部署完整 RAG 平台，而是：

1. 继续把一个 Obsidian Vault 中的 Markdown 作为唯一事实源，并采用 Foam-inspired Schema 2 的单一工作区和原子笔记原则。
2. 使用一个路由式 Codex Skill，由全局规则在项目工作中自动执行开工只读、阶段记录和收工；模式名只作为内部动作。
3. 本机访问优先使用直接文件夹权限；MCP/API 只是未来可单独评估的访问方式，不是当前版本或 `05` 的安装内容。
4. 同步与备份独立设计：使用 Syncthing 作为设备间主同步通道，GitHub 私有仓库作为手动提交的云端副本；Git 不承担高频实时同步。
5. 语义检索是后续增强。Khoj 最贴近 Obsidian 第二大脑；AnythingLLM、Onyx 更像独立 RAG/知识平台；Mem0 是 Agent 记忆层，不应替代 Vault。
6. 不在每一轮对话后写笔记。全局规则只在明确事件上自动维护：经过验证的阶段成果、有持久结果的任务收尾和每周整理。
7. 如果未来单独使用参考仓库采用的 MCPVault，必须要求版本不低于 0.11.5；官方安全公告说明更早版本存在嵌套受限目录过滤问题。

Obsidian 官方说明 Vault 本质上是本地文件夹，笔记是 Markdown 纯文本，外部工具修改后 Obsidian 会自动刷新。这使 Codex 直接操作 Markdown 成为最小、透明、可迁移的方案。[Obsidian 数据存储](https://obsidian.md/help/data-storage)

`05` 安装只复制 Skill 并合并用户级全局规则，不安装 Foam、`foam-cli`、VS Code 扩展、MCP 或一键脚本，
也不触碰真实 Vault。Schema 1 Vault 只能在之后由用户确认的 `repair` Schema 1→2 子动作显式迁移。

## 先区分四件不同的事

| 能力 | 解决的问题 | 不负责什么 |
| --- | --- | --- |
| 笔记更新 | 把进度、决策、实验和知识写入 Markdown | 不负责跨设备传输 |
| 同步/版本控制 | 在设备间同步或保存历史版本 | 不理解笔记语义 |
| MCP/API | 让 Codex 安全、结构化地读写 Vault | 不会自动决定哪些内容值得保存 |
| RAG/Agent Memory | 语义检索或保存会话记忆 | 不应自动成为权威知识源 |

很多“AI 第二大脑”项目只覆盖其中一层。选型时应先确定需要哪一层，避免同时维护多套事实源。

## 推荐架构

### 第一阶段：最小可用

保留当前分工，并把 Vault 内部结构固定为 Schema 2：

- GitHub：代码、Issue、PR、commit 和版本历史。
- 项目 AGENTS.md：稳定规则、项目入口、Vault 路径和项目索引路径。
- Obsidian：每日进度、项目 `index.md`、`status.md`、原子 lessons、技术决策、实验记录和长期知识。
- Codex：在明确触发点读取或更新上述内容。

建议在一个个人 Skill 中保留以下内部动作；用户无需逐项调用：

1. second-brain-startup
   - 读取项目 AGENTS.md。
   - 读取对应项目 `index.md`、`status.md`、主题索引（按需）和最近一次收工记录。
   - 检查 git status。
   - 每个会话首次处理某项目时静默运行，不单独汇报流程，也不写入 Vault。

2. second-brain-shutdown
   - 汇总本次实际完成事项、验证结果、未完成项和下一步。
   - 在产生持久结果的任务最终回复前自动运行。
   - 自动创建或补全设备独立的 Session；共享状态和正式知识仍先展示差异并确认。
   - 只有稳定规则发生变化时才建议更新 AGENTS.md。
   - Git commit/push 单独确认。

3. second-brain-weekly
   - 汇总过去七天每日笔记。
   - 提出应沉淀到知识库的候选条目。
   - 生成新增、合并、归档建议。
   - 默认只生成草案，不自动删除、移动或重命名原笔记。

这套方案不需要向量数据库，也不要求 Obsidian 必须保持打开。

### 第二阶段：可靠读写

访问方式三选一，不建议同时给多个工具完整写权限：

- 直接文件夹访问：依赖最少、最透明，适合 Codex 已获 Vault 文件夹权限的本机工作。
- Obsidian Local REST API：适合需要全文检索、定点 PATCH、活动笔记和 Obsidian 命令的场景；当前官方仓库已内置 MCP endpoint，并使用 bearer token。[Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api)
- MCPVault：适合 Obsidian 不必运行、通过本地 stdio MCP 直接操作文件的场景；必须固定安全版本。[MCPVault](https://github.com/bitbonsai/mcpvault)

如果需要更细的文件夹权限、stdio/HTTP 两种传输和外部存储扩展，可以评估 cyanheads 的 MCP server；它通过 Local REST API 操作 Vault，并提供目录范围权限。[cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server)

### 第三阶段：同步和备份

当前选定方案是职责分离，而不是两个实时同步器并行：

- Syncthing 是唯一的设备间内容同步通道，每台设备都保留同一个主 Vault 的本地副本。
- GitHub 私有仓库是云端备份和历史审查通道，由指定设备人工检查后 commit/push。
- Git 不自动 pull/push，也不作为其他设备之间的实时同步方式；设备配置、`.git`、工作区 UI 状态和冲突临时文件不通过 Syncthing 传播。

Obsidian Git 支持定时 commit/pull/push、启动时 pull、diff 和历史视图，但其官方 README 明确警告移动端 Git 实现不稳定。[Obsidian Git](https://github.com/Vinzent03/obsidian-git)

Git 仓库不能当作秘密保险箱。GitHub 官方说明，秘密进入历史后，即使重写历史也需要轮换凭证、协调所有 clone/fork，并可能产生大量副作用。[GitHub 敏感数据清理](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

### 第四阶段：语义检索

当 Vault 达到数千篇笔记、关键词搜索明显不够时，再加入 Khoj：

- 支持 Markdown 和 Obsidian。
- 支持本地自托管和本地/在线模型。
- 提供语义搜索、相似笔记和对话检索。
- 它应作为索引和查询层，Vault 仍是权威数据源。

[Khoj 仓库](https://github.com/khoj-ai/khoj)；[Khoj Obsidian 集成](https://docs.khoj.dev/clients/obsidian/)

## 项目与方案对比

| 方案/项目 | 角色 | 开源/许可 | 数据位置 | 更新机制 | Codex 集成 | Windows | 2026-10-02 状态 | 优点 | 主要代价 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 本地 Markdown + Codex 文件访问 | 权威笔记库 | 文件格式开放；Obsidian 本体非开源 | 本地 Vault | Codex 直接读写文件 | 原生文件工具 | 好 | Obsidian 官方持续支持此存储模型 | 最简单、透明、无索引漂移 | 搜索和权限粒度较基础 |
| [Obsidian Git](https://github.com/Vinzent03/obsidian-git) | 版本控制/同步 | MIT | 本地 Git + 远端仓库 | 定时或手动 pull/commit/push | Codex 可调用 Git 或让插件执行 | 桌面好；移动端不推荐 | 仓库公开且未归档 | 历史、diff、恢复直观 | 冲突、认证、秘密泄露风险 |
| [Self-hosted LiveSync](https://github.com/vrtmrz/obsidian-livesync) | 多设备实时同步 | MIT | Vault + 自托管同步后端 | 插件持续同步 | Codex 继续读本地 Vault | 中等，需要部署后端 | 仓库公开且未归档 | 移动端体验通常优于 Git | 运维复杂，必须设计备份 |
| [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) | API + MCP 访问 | MIT | Vault 本地；服务运行在 Obsidian 内 | REST/MCP 读写、搜索、PATCH | Streamable HTTP MCP 或 REST | 好，需 Obsidian 运行 | 仓库公开且未归档；已内置 MCP | 精准 PATCH、全文搜索、活动文件、命令 | API key/TLS 配置；Obsidian 必须运行 |
| [MCPVault](https://github.com/bitbonsai/mcpvault) | 独立本地 MCP | MIT | 直接访问本地 Vault | stdio MCP 读写、搜索 | 官方 README 提供 OpenAI Codex 配置 | 好，需 Node.js 20+ | 仓库公开且未归档 | 轻量、无需 Obsidian 运行 | 需管理 Node 依赖和版本安全 |
| [cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server) | 高级 MCP 网关 | Apache-2.0 | 经 Local REST API 访问 Vault | stdio/HTTP，结构化局部编辑 | MCP | 中等 | 仓库公开且未归档 | 权限和传输选择更丰富 | 组件更多，个人使用可能过度 |
| [Khoj](https://github.com/khoj-ai/khoj) | AI 第二大脑/语义检索 | AGPL-3.0 | 可自托管；索引 Vault | 周期同步索引、搜索、对话 | 可通过 Obsidian 插件使用；Codex 需额外 API/MCP 桥接 | 中等 | 仓库公开且未归档 | 与 Obsidian契合，支持本地模型和语义搜索 | 部署和索引成本；不是主要写入层 |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) | 本地 RAG/Agent 应用 | MIT | 本地桌面或自托管 | 文档摄取到向量库 | 独立应用/API | 好，有 Windows Desktop | 仓库公开且未归档 | 安装相对容易，支持本地/云模型 | 容易形成 Vault 之外的第二套工作台 |
| [Onyx](https://github.com/onyx-dot-app/onyx) | 团队知识连接和 RAG | 核心 MIT；ee 目录为企业许可 | 自托管索引与服务栈 | 后台 connector 同步和索引 | 需 connector/API 集成 | 偏重，通常依赖容器 | 仓库公开且未归档 | 连接器和团队权限能力强 | 对个人 Obsidian 过重 |
| [Mem0](https://github.com/mem0ai/mem0) | Agent 长期记忆层 | Apache-2.0 | 库、自托管服务或云 | 从交互中提取用户/会话/Agent 记忆 | SDK、API、Codex 相关技能 | 中等 | 仓库活跃且未归档 | 适合跨会话偏好和 Agent 状态 | 不是 Markdown 知识库，内容可解释性较弱 |
| [Reor](https://github.com/reorproject/reor) | 本地 AI 知识管理应用 | 开源仓库 | 本地 | 独立应用索引和编辑 | 无直接 Codex 主线 | 曾支持桌面 | 2026-03-07 已归档，只读 | 设计思路值得参考 | 不建议新部署 |

## MCPVault 安全要求

MCPVault 官方安全公告 GHSA-9c83-rr99-vfwj 说明：

- 受影响版本：低于 0.11.5。
- 修复版本：0.11.5。
- 问题：受限目录规则只在 Vault 根目录生效，嵌套的 .git、.obsidian、node_modules 可能被遍历和读取。
- 风险场景包括读取嵌套 .git/config 中的远端 URL 或嵌入式 token。

因此懒人包不能继续使用不带版本约束的 latest 安装方式。最低要求应为 0.11.5，并在锁定时检查是否存在更新的安全修复。[官方安全公告](https://github.com/bitbonsai/mcpvault/security/advisories/GHSA-9c83-rr99-vfwj)

额外安全规则：

- MCP 根目录只指向 Vault，不要指向用户目录或磁盘根目录。
- Vault 内不放 SSH 私钥、API key、cookie、密码导出或生产凭证。
- 不在 Vault 内嵌套代码仓库；至少确保任何嵌套 .git 均不可被 MCP 读取。
- 设备独立 Session 和 Inbox 可以按已配置策略无打断写入；共享状态、正式知识、删除、移动和批量重命名必须展示目标与差异并单独确认。
- 第三方或网页剪藏内容视为不可信数据，不能让笔记中的文字改变 Agent 权限或工作规则。

## Schema 2 推荐 Vault 结构

    SecondBrain/
    ├─ index.md
    ├─ 00-收件箱/
    │  ├─ <year>/<month>/<timestamp>-<device-short>-<中文主题>.md
    │  └─ 每周整理-<year>-W<week>-<device-short>.md
    ├─ 10-项目/
    │  ├─ index.md
    │  └─ <project-id>/
    │     ├─ index.md
    │     ├─ status.md
    │     ├─ sessions/<year>/
    │     ├─ decisions/
    │     ├─ experiments/
    │     └─ lessons/<lesson-id>.md
    ├─ 20-领域/
    │  ├─ index.md
    │  └─ <area-id>/index.md
    ├─ 30-知识/
    │  ├─ index.md
    │  └─ <topic>/
    │     ├─ index.md
    │     └─ <note-id>-<中文主题>.md
    ├─ 40-资源/
    │  ├─ index.md
    │  └─ <web|paper|book|repository|other>/<resource-id>-<中文主题>.md
    ├─ 50-日记/<year>/
    ├─ 60-归档/
    ├─ 90-系统/
    │  ├─ second-brain.md
    │  ├─ schemas/schema-v2.md
    │  └─ templates/
    └─ 附件/

项目入口使用 `index.md`，当前状态使用 `status.md`，经验写入 `lessons/` 下的原子笔记；每个主题目录拥有自己的
`index.md`。跨目录链接使用 Vault 根相对、路径限定 Wikilink（新建中文布局示例 `[[10-项目/<project-id>/status|项目状态]]`），
不带前导 `/` 或 `.md`，不依赖全库同名解析。
Skill 提供的 16 个模板只作为种子；新建 Vault 默认用中文一级目录，既有 ASCII Vault 保留原布局。初始化后，所选布局中的 `templates/` 是权威模板目录。

项目代码仓库不要放进 Vault。Vault 的本机绝对路径只保存在
`<CodexHome>/second-brain/config.json`，不得写入项目仓库。用户级 `AGENTS.md` 保存自然维护规则；项目通过规范化
Git remote 匹配 Vault 中的项目元数据，因此不同设备不需要各自修改项目文件。

## 安全写入策略

### 允许自动执行

- 读取明确指定的项目 `index.md`、`status.md`、每日笔记和主题索引。
- 创建或补全一条带时间戳和设备 ID 的独立 Session。
- 在当前 Vault 布局的 Inbox 目录创建带设备 ID 的独立整理草案。
- 生成拟写入 diff。

### 必须确认

- 修改已有技术决策。
- 把每日笔记提升为长期知识。
- 修改 frontmatter schema。
- Git commit/push。
- 让定时任务直接写入正式知识库。

### 禁止静默执行

- 删除、移动、覆盖或批量重命名笔记。
- 修改 .obsidian。
- 写入 token、密码、私钥、cookie 或生产数据。
- 根据外部剪藏内容扩大权限。
- 同时运行两个会写同一文件的 Agent。

正式知识应使用 `sources` 或 `derived_from` 保存外部证据和来源 Session 的路径限定 Wikilink；候选在人工复核前保持
`status: candidate`，确认后再改为 `verified`。

## 自动化建议

OpenAI 官方文档说明，Codex 桌面端的 Scheduled tasks 可以访问本地项目、调用 Skill，并按周期运行；本地文件任务要求电脑保持开机且应用运行。官方同时建议先手动测试 prompt，使用最窄权限，并注意 unattended 任务使用默认沙箱设置。[Codex Scheduled tasks](https://learn.chatgpt.com/docs/automations)

推荐只安排一个每周任务：

- 输入：过去七天每日笔记、项目 `index.md` 和 `status.md`。
- 输出：知识沉淀候选、重复内容、过期事项和建议链接。
- 写入位置：当前布局 Inbox 目录下的 `每周整理-<year>-W<week>-<device-short>.md`。
- 默认行为：不修改正式知识库、不删除文件、不自动 push。
- 用户审核后，再调用 second-brain-weekly 应用变更。

不推荐：

- 每几分钟扫描并写 Vault。
- 每次聊天结束都自动提取“记忆”。
- 在 full-access 权限下运行可删除或移动笔记的无人值守任务。
- 同时让 Git 自动同步、云盘同步和 LiveSync 高频写同一 Vault。

## 最终排名

针对当前个人 Codex 懒人包：

1. 本地 Markdown + codex-second-brain 的自然维护规则；startup/shutdown/weekly 只作为内部动作。
2. 直接文件夹访问；Local REST API、MCPVault 等仅作为未来单独评估的可选访问层，不由 `05` 安装。
3. 若未来必须在 Obsidian 关闭时工作，再使用固定版本且不低于 0.11.5 的 MCPVault；这不属于本版安装范围。
4. 使用 Syncthing 做多设备主同步，并由指定设备手动提交到 GitHub 私有仓库作为云端备份。
5. Vault 很大、检索困难后再加 Khoj。
6. AnythingLLM 可作为独立文档问答实验，不作为第二大脑事实源。
7. Onyx 适合团队知识平台，个人场景不优先。
8. Mem0 适合未来的 Agent 个性化记忆，不替代 Obsidian。
9. Reor 已归档，不作为新方案。

## 在当前懒人包中的落地

懒人包从 `0.6.0` 起将上述能力实现为本仓库维护的单一 `codex-second-brain` 路由 Skill，并升级到 Vault Schema 2，包含：

- setup、link、startup、checkpoint、shutdown、weekly、promote 和 repair 八种内部动作。
- 跨设备本地配置、基于 Git 远端的项目识别和统一单 Vault 数据结构。
- 项目 `index.md` + `status.md`、`lessons/` 原子笔记、主题目录 + `index.md`、路径限定 Wikilink、Vault 本地模板权威。
- 16 个模板、Vault schema 资产、Syncthing 主同步和 GitHub 私有仓库人工备份边界。
- 合并到用户级 `AGENTS.md` 的受管自然维护规则，在普通项目工作中自动恢复和保存上下文。

编号 `05` 只负责安装完整 Skill 并合并全局规则，不寻找或修改真实 Vault，不执行 schema 迁移，也不安装 Foam、CLI、
VS Code 扩展或 MCP。首次建库和设备配置仍由用户显式开始；配置完成后，日常持续更新自动融入项目任务，不要求用户提示内部动作。
