---
name: codex-second-brain-pack
description: 通过对话安装本仓库维护的 codex-second-brain Skill，配置本机 Syncthing 的暂停式安全基线，并把自然维护规则合并到用户级 AGENTS.md。
---

# 第二大脑 Skill 安装包

仅在用户选择 `05` 或“全部”时执行本 Skill。

## 目标

把本仓库内置的 Schema 2 `codex-second-brain` 完整目录安装到用户级 Skill 目录，将自然维护规则合并到
`<CodexHome>/AGENTS.md`，并完成本机第二大脑设备配置和 Syncthing 后台登录启动。

选择 `05` 即授权本次安装所需的、限定在本机的增量配置；不得把这份授权扩展到远端设备、同步网络、GitHub 或 Vault 内容迁移。
配置完成后，普通项目工作会自动恢复上下文、记录有持久价值的结果并在任务结束前收尾，不要求用户手动提醒内部模式。
已有 Schema 1 配置或 Vault 不在安装阶段迁移；以后只能由 `repair` 的 Schema 1→2 子动作，在展示差异并获得明确确认后迁移。

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
检查有效全局规则是否受 `AGENTS.override.md` 遮蔽；若需合并到 override，按共享规则单独展示差异并确认，
记录实际规则目标。下文 `<CodexHome>/AGENTS.md` 是默认目标；用户确认改用有效 override 后，在实际目标上执行相同的受管区块检查。

## 本机同步配置

本节只在 `05` 安装期间运行；日常项目工作和普通 `setup` 不自动重配或启动 Syncthing。

1. 读取 [本机同步引导规则](../../bundled-skills/codex-second-brain/references/syncthing-bootstrap.md) 和锁文件中的 Syncthing 版本/平台校验值。
2. 通过对话中由 Codex 调用的 `bundled-skills/codex-second-brain/scripts/setup_syncthing.py` 做只读预检；不要要求用户手动运行脚本、打开 GUI 或输入 Syncthing 命令。
3. 若设备配置文件不存在，不视为懒人包安装失败：从对话一次性询问已有 Vault 路径，路径有效后创建本机设备配置。路径必须是已存在目录，不创建空 Vault。若用户无法提供有效路径，或遇到多个配置候选、Schema 1、损坏配置或自启动项冲突，只暂停 Syncthing 本机配置并报告；第二大脑 Skill、全局规则及其他已选 Skill 仍可安装。
4. 若设备配置合法但缺少安全推导字段，保留未知字段并只补齐稳定设备 ID、设备标签（优先现有值，否则主机名）及缺失的 Schema 2 默认字段。不得覆盖用户已有 Vault、同步或 GitHub 备份设置。
5. 只在 Syncthing 缺失时安装锁定的官方版本并核验 SHA-256；已有版本不自动升级或降级。配置写入前备份原文件。只允许本机监听，关闭全局/LAN 发现、中继和 NAT 映射；新增或复用目标 Vault 文件夹但保持暂停。
6. 若已有远端设备或目标 Vault 以外的活动文件夹，禁止改配置、忽略规则、自启动项或启动实例；先保留其他已完成的 Skill 安装并报告冲突。不要连接服务器、添加设备、打开浏览器、触发文件传输或更改防火墙。
7. 安全合并 `/.git`、`/.claudian`、`/.obsidian/workspace*` 到本机 `.stignore`；保留用户规则并去重。忽略文件内容不由 Syncthing 跨设备传播。
8. 注册或复用当前用户登录时启动的后台项：Windows Task Scheduler、macOS LaunchAgent、Linux systemd 用户服务；不可用时使用 XDG 桌面自启动。既有项必须启用且参数符合基线；禁用或有歧义时停止相关写入。新建启动项显式固定 loopback GUI 和暂停状态；检查进程及登录服务环境中的 `STGUIADDRESS`、`STPAUSED`、`STUNPAUSED`、`STHOMEDIR`、`STCONFDIR`、`STDATADIR`，冲突或无法验证时停止相关写入。使用 `--no-browser`，不启动网页浏览器。
9. 完成后读取配置并验证启动项、后台进程、Vault 路径、暂停状态、网络开关、忽略规则、远端数量和连接状态。本机 API 只允许访问 `127.0.0.1`，禁用代理并拒绝重定向；必须实际核对 API 的本机设备 ID 与 profile 一致、设备列表只有本机、无远端活动连接、目标文件夹路径一致且只关联本机并保持暂停，否则不得报告配置成功。没有远端设备时明确说明实际跨设备同步未验证。

## 执行要求

1. 读取内置源目录的全部文件，确认 `SKILL.md`、六个 Schema 2 reference、`assets/vault-schemas/schema-v2.md`、
   `assets/vault-templates/` 下恰好 16 个模板、设备配置模板和全局规则资产完整可读。
2. 读取目标目录。目录不存在时标记为待安装；内容相同则标记为 `already-current`。
3. 目标目录已存在且内容不同或来源不明时，先展示新增、删除和修改的路径。
4. 通过对话让用户选择替换、手动合并或跳过；确认替换或应用合并后，先备份整个目录再写入。未确认时保持 `pending`，不要静默覆盖。
5. 单独读取 `<CodexHome>/AGENTS.md`：
   - 文件不存在时，展示将创建的内容并在确认后写入受管区块。
   - 没有对应标记时，展示追加差异，备份已有文件后再确认合并。
   - 已有完全相同区块时标记为 `already-current`。
   - 已有一对完整标记但区块内容不同时，展示差异并让用户选择更新、手动合并或跳过，不得追加第二份。
   - 标记残缺、嵌套或重复时，停止自动修改并报告 `pending`；保留原文件，展示需手动修复的范围。
6. 替换或合并后重新读取目标 Skill 和 `AGENTS.md`，验证 frontmatter、目录结构、全部 references 链接、
   schema 资产、16 个模板及 Schema 2 版本字段。设备配置模板先替换一组安全示例值再解析 JSON；不得要求未渲染占位符本身是合法 JSON。最后确认受管区块恰好出现一次且内容与源资产一致。
7. 从 `sources.lock.json` 记录当前懒人包版本、`vaultSchemaVersion` 和 `deviceConfigSchemaVersion` 及本次快照身份，
   按共享规则分别报告文件安装、客户端发现和功能验证状态；规则尚未刷新或被遮蔽不能标记为已生效。
8. 安装阶段仅按“本机同步配置”执行受限设置；不得读取或改写 Vault 笔记内容、迁移 Schema、配置远端设备、GitHub 备份、MCP 或每周自动化。

### 安装阶段验证清单（不是 Vault 迁移）

- 六个 reference 和 schema 资产均可读取；模板必须精确包含 `root-index`、`collection-index`、`project-index`、
  `project-status`、`session`、`decision`、`experiment`、`lesson`、`area-index`、`topic-index`、`knowledge`、`resource`、
  `inbox-note`、`daily`、`weekly-review`、`system-manifest`。
- `sources.lock.json` 的包版本与内置源 `packageVersion` 必须一致，Vault schema 为 2，设备配置 schema 为 2；
  设备配置模板和 Vault schema 资产不得声明旧版本。
- 每个模板必须声明 `schema_version: 2`、`id`、`title`、`type`、`created`、`updated`；`id` 占位符落盘前必须替换为对应类型前缀的 UUIDv4。
- 复制后的 Skill 与源目录逐文件一致，且其 references 链接、16 个模板和 schema 资产均存在。
- 安装时核对本机配置与冲突预检、启动项参数、后台运行及不自动打开浏览器；任何状态不符都应停止相关配置并报告。目标 Vault 文件夹必须保持暂停。
- `<CodexHome>/AGENTS.md` 的 `codex-second-brain-managed` 起止标记恰好各出现一次，受管区块与源资产一致；其他全局规则保持不变。
- 安装会只读确认 Vault 根路径，并且只可能读取或增补该根目录的 `.stignore`；不遍历笔记、不创建 Vault 结构、不迁移笔记或 Schema。
  Schema 1→2 迁移必须稍后显式调用 `repair` 子动作并再次确认。

## 安全边界与报告

不要索要或保存 Vault 密码、API token、项目秘密或其他凭证。完成后报告懒人包版本、可用时的仓库 commit、
Skill 与全局规则的目标和状态、备份位置，以及是否需要重启 Codex。

全局规则以设备配置存在且 Vault 可访问为启用条件，因此安装后、首次建库前不会介入普通项目工作。首次建库和首次
项目关联仍需确认目标及变更；已有同名目录或文件不得静默覆盖。若检测到 Schema 1，只报告可迁移项，不得在安装阶段自动升级。
