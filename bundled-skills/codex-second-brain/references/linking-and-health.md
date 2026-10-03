# 链接与健康检查（Schema 2）

创建或批量验证内部链接、执行 `weekly` 健康检查、执行 `repair` 时读取本参考。迁移旧路径只按 [migration-v1-to-v2.md](migration-v1-to-v2.md) 执行。

## 路径限定 Wikilink

内部链接从 Vault 根计算，使用 `[[path]]` 或 `[[path|中文标题]]`：

```text
[[10-Projects/index|项目]]
[[10-Projects/<project-id>/status|项目状态]]
[[10-Projects/<project-id>/lessons/<lesson-id>-<slug>|经验标题]]
[[30-Knowledge/<topic-id>/index|主题]]
[[30-Knowledge/<topic-id>/<knowledge-id>-<slug>|知识标题]]
[[40-Resources/<source-type>/<resource-id>-<slug>|资源标题]]
```

必须满足：

1. 路径不以 `/` 开头，不含 `./`、`../`、绝对磁盘路径、查询字符串、标题或块后缀。
2. 路径不带 `.md`，只使用正斜杠；路径段使用文件系统安全 ASCII。显示别名可以是简体中文。
3. 目标必须解析到 Vault 内现有文件。除根入口文件自身外，不创建 `[[index]]`、`[[status]]` 等只含 basename 的裸链接；根 `index.md` 不需要其他笔记反向链接。
4. 不使用 Markdown 文件链接、Obsidian URI 或 Foam 引用定义代替受管内部链接。HTTPS 外部来源不属于 Wikilink。
5. YAML 中的 Wikilink 必须加引号。`knowledge_scopes`、`sources`、`derived_from`、`supersedes` 中的 Vault 目标同样遵守本规则。
6. 路径发生变化时更新引用，不复制正文来保持同步。

## 索引覆盖

- 根 `index.md` 必须链接四个 collection index，且目标存在。
- `10-Projects/index.md` 链接每个项目入口；项目入口至少链接现有 `status.md`。Session、Decision、Experiment、Lesson 只在实际文件存在后加入导航。
- `20-Areas/index.md` 链接每个 Area 的 `index.md`。
- `30-Knowledge/index.md` 链接每个主题 `index.md`；主题索引链接其现有原子 Knowledge。
- `40-Resources/index.md` 链接各 source-type 范围内的资源；资源必须位于 `web`、`paper`、`book`、`repository` 或 `other`。
- 项目入口保存身份和导航；生命周期和当前工作状态只从 `status.md` 解析。重复正文或重复状态属于需确认问题。

索引缺口、孤儿、重复目标或循环不是自动移动、合并或删除的理由。

## 健康检查

`weekly` 只读检查并把结果写入设备独立 Inbox 草案；`repair` 生成分组差异并在确认后修复。

1. **同步与并发**：查找 `.sync-conflict-*` 等明显冲突、未完成同步迹象和同一目标的其他写入者；无法确认时阻断共享写入。
2. **元数据**：检查 `schema_version: 2`、`id`、`title`、`type`、`created`、`updated`，以及类型所需字段和状态。
3. **身份唯一性**：检查 `id` 的类型前缀、UUIDv4 和全 Vault 唯一性；不能从标题或文件名补造 ID。
4. **链接**：报告裸 Wikilink、前导 `/`、`.md`、相对路径、路径穿越、歧义目标、断链和错误 source-type；外部 URL 单独处理。
5. **索引**：验证根、四个 collection、项目、Area 和 Topic 的覆盖关系；索引只导航，不复制正文。
6. **类型边界**：验证项目入口没有生命周期 `status`，`status.md` 有合法状态；Lesson 和 Knowledge 是单主题原子文件；Resource 有合法 `source_type` 和来源。
7. **孤儿**：报告未从任何 Topic、Area 或项目范围可达的正式 Knowledge、Lesson 和 Resource。Inbox、Daily、Session、Archive、System 和各级 index 不按孤儿处理，也不因孤儿自动删除。
8. **模板权威**：确认新建类型优先使用 `90-System/templates/`，并检查本地模板与 Schema 2 的兼容性；内置 assets 不能覆盖定制模板。
9. **配置职责**：验证设备配置仍为 Schema 2、Syncthing 主同步和 GitHub 人工备份；不读取或暴露凭证。

## 报告等级

- **阻断**：冲突文件、并发写入、路径越出 Vault、重复 ID、未知 type/status、迁移映射歧义或验证无法运行。保持原状。
- **需确认**：断链、索引缺口、正式内容孤儿、模板差异、状态重复、移动/重命名/合并或批量链接重写。展示路径和差异后再应用。
- **提示**：不影响正确性的可选别名、标签或尚待整理的候选。只记录，不自行修改。

检查结束后重新读取涉及目标。目标变化、出现新冲突或两次有证据的修复尝试失败时停止；不得自动删除、覆盖、合并或扩大扫描范围。
