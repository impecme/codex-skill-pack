<!-- codex-second-brain-managed:start -->
## 第二大脑自然维护

当 `<CodexHome>/second-brain/config.json` 存在且 Vault 可访问时，把第二大脑维护自然融入 Git 项目工作，并使用 `codex-second-brain` Skill。`startup`、`checkpoint` 和 `shutdown` 是内部动作，不要求用户记住或选择。

- Vault 内的 `90-System/schemas/schema-v2.md`、`90-System/second-brain.md` 和 `90-System/templates/` 是运行时 schema 与模板权威；项目身份入口是 `10-Projects/<project-id>/index.md`，生命周期和当前状态只在同目录 `status.md`。setup 只从本 Skill 的 assets 复制缺失内容。
- 每个会话首次对项目开展实质性工作前静默只读恢复；只加载当前任务需要的项目状态、最近记录和相关知识。
- 只有产生经过验证且以后仍有价值的成果时才记录 checkpoint；收尾时复用同一条 Session，不按命令或回复重复建笔记。
- 分级策略允许自动创建或追加设备独立的 Session 和 Inbox；Daily 只作人工导航，不复制 Session 正文。Vault 不可用或同步冲突时不打断项目工作。
- 首次建库或关联仓库、修改共享状态或正式知识、接受决策、调整 schema 或同步设置、移动或删除笔记，以及 Git commit/push，继续遵守 Skill 既有确认边界。
- 内部链接必须使用 Vault 根相对、路径限定的 Wikilink；每条事实只保留一份权威记录，其他位置使用链接或短摘要。
<!-- codex-second-brain-managed:end -->
