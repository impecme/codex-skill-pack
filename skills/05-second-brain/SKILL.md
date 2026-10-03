---
name: codex-second-brain-pack
description: 通过对话安装本仓库维护的 codex-second-brain Skill，并把自然维护规则合并到用户级 AGENTS.md，使第二大脑自动融入跨设备、跨项目工作。
---

# 第二大脑 Skill 安装包

仅在用户选择 `05` 或“全部”时执行本 Skill。

## 目标

把本仓库内置的 Schema 2 `codex-second-brain` 完整目录安装到用户级 Skill 目录，并把它的受管自然维护规则合并到
`<CodexHome>/AGENTS.md`。安装阶段只安装 Skill 和全局规则，不寻找、创建或修改真实 Vault，不创建定时任务，也不修改项目文件。

用户仍需通过“建立或接管第二大脑”完成一次性 Vault 和设备配置。配置完成后，普通项目工作会自动恢复上下文、
记录有持久价值的结果并在任务结束前收尾，不要求用户手动提醒内部模式。已有 Schema 1 Vault 不在安装阶段迁移；
以后只能由 `repair` 的 Schema 1→2 子动作，在展示差异并获得明确确认后迁移。

## 固定来源

先读取仓库根目录的 `sources.lock.json`，只使用 `bundled-codex-second-brain` 条目：

- 本仓库源目录：`bundled-skills/codex-second-brain`
- 全局规则源文件：`bundled-skills/codex-second-brain/assets/global-agents-section.md`
- Vault schema 资产：`bundled-skills/codex-second-brain/assets/vault-schemas/`
- Vault 模板资产：`bundled-skills/codex-second-brain/assets/vault-templates/`（应有 16 个模板）
- Vault schema 和设备配置 schema：以 `sources.lock.json` 为准
- 目标目录：`<SkillRoot>/codex-second-brain`
- 全局规则目标：`<CodexHome>/AGENTS.md` 中 `codex-second-brain-managed` 标记包围的受管区块

`<SkillRoot>` 默认是 `<CodexHome>/skills`；如果当前环境使用其他用户级 Skill 目录，以实际发现的目录为准。

## 执行要求

1. 读取内置源目录的全部文件，确认 `SKILL.md`、五个 Schema 2 reference、`assets/vault-schemas/schema-v2.md`、
   `assets/vault-templates/` 下恰好 16 个模板、设备配置模板和全局规则资产完整可读。
2. 读取目标目录。目录不存在时标记为待安装；内容相同则标记为 `already-current`。
3. 目标目录已存在且内容不同或来源不明时，先展示新增、删除和修改的路径，再备份整个目录。
4. 通过对话让用户选择替换、手动合并或跳过；未确认时保持 `pending`，不要静默覆盖。
5. 单独读取 `<CodexHome>/AGENTS.md`：
   - 文件不存在时，展示将创建的内容并在确认后写入受管区块。
   - 没有对应标记时，展示追加差异，备份已有文件后再确认合并。
   - 已有完全相同区块时标记为 `already-current`。
   - 已有不同区块、残缺标记或重复区块时，展示差异并让用户选择更新、手动合并或跳过，不得追加第二份。
6. 替换或合并后重新读取目标 Skill 和 `AGENTS.md`，验证 frontmatter、目录结构、全部 references 链接、
   schema 资产、16 个模板及 Schema 2 版本字段。设备配置模板先替换一组安全示例值再解析 JSON；不得要求未渲染占位符本身是合法 JSON。最后确认受管区块恰好出现一次且内容与源资产一致。
7. 从 `sources.lock.json` 记录当前懒人包版本、`vaultSchemaVersion` 和 `deviceConfigSchemaVersion`；能够解析本仓库 Git commit
   时一并报告，不能解析时不得编造。
8. 安装阶段不得定位或写入 Vault，不得创建 `<CodexHome>/second-brain/config.json`，不得配置 Syncthing、GitHub 备份、MCP 或每周自动化。

### 安装阶段验证清单（不是 Vault 迁移）

- 五个 reference 和 schema 资产均可读取；模板必须精确包含 `root-index`、`collection-index`、`project-index`、
  `project-status`、`session`、`decision`、`experiment`、`lesson`、`area-index`、`topic-index`、`knowledge`、`resource`、
  `inbox-note`、`daily`、`weekly-review`、`system-manifest`。
- `sources.lock.json` 的包版本为 `0.6.0`，`packageVersion` 为 `0.6.0`，Vault schema 为 2，设备配置 schema 为 2；
  设备配置模板和 Vault schema 资产不得声明旧版本。
- 每个模板必须声明 `schema_version: 2`、`id`、`title`、`type`、`created`、`updated`；`id` 占位符落盘前必须替换为对应类型前缀的 UUIDv4。
- 复制后的 Skill 与源目录逐文件一致，且其 references 链接、16 个模板和 schema 资产均存在。
- `<CodexHome>/AGENTS.md` 的 `codex-second-brain-managed` 起止标记恰好各出现一次，受管区块与源资产一致；其他全局规则保持不变。
- 以上检查只验证安装内容和受管区块，不创建或扫描真实 Vault，也不执行 Schema 1 到 Schema 2 的迁移；迁移必须稍后显式调用
  `repair` 的 Schema 1→2 子动作并再次确认。

## 安全边界与报告

不要索要或保存 Vault 密码、API token、项目秘密或其他凭证。完成后报告懒人包版本、可用时的仓库 commit、
Skill 与全局规则的目标和状态、备份位置，以及是否需要重启 Codex。

全局规则以设备配置存在且 Vault 可访问为启用条件，因此安装后、首次建库前不会介入普通项目工作。首次建库和首次
项目关联仍需确认目标及变更；已有同名目录或文件不得静默覆盖。若检测到 Schema 1，只报告可迁移项，不得在安装阶段自动升级。
