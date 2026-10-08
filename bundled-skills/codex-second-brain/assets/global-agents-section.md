<!-- codex-second-brain-managed:start -->
## 第二大脑自然维护

当 `<CodexHome>/second-brain/config.json` 存在且 Vault 可访问时，把第二大脑维护自然融入 Git 项目工作，并使用 `codex-second-brain` Skill。`startup`、`checkpoint` 和 `shutdown` 是内部动作，不要求用户记住或选择。

- 若 `<CodexHome>/second-brain/sync-onboarding.json` 存在且 `status` 不是 `active`，或包含任何 `pendingOperation`（即使 `status` 是 `active`），说明双机首次播种/核验尚未结束或操作处于 HOLD。继续完成不依赖 Vault 的主要工程工作，但暂停对 Vault 的自动恢复、Session/Inbox 写入、checkpoint、shutdown 和其他自然维护；只允许继续 05 引导明确要求的配置/验证或恢复步骤。不得把未完成状态静默改为 `active`，也不得忽略 pending 标记。

- Vault 内所选布局的 `schemas/schema-v2.md`、`second-brain.md` 和 `templates/` 是运行时 schema 与模板权威；新建 Vault 默认中文一级目录，既有 ASCII 布局继续使用原路径。项目身份入口位于逻辑目录 Projects 下的 `<project-id>/index.md`，生命周期和当前状态只在同目录 `status.md`。每次读写先核验布局；混合、冲突或无法识别时停止 Vault 写入。setup 只从本 Skill 的 assets 复制缺失内容。
- 每个会话首次对项目开展实质性工作前静默只读恢复；只加载当前任务需要的项目状态、最近记录和相关知识。
- 只有产生经过验证且以后仍有价值的成果时才记录 checkpoint；收尾时复用同一条 Session，不按命令或回复重复建笔记。
- 分级策略允许自动创建或追加设备独立的 Session 和 Inbox；Daily 只作人工导航，不复制 Session 正文。Vault 不可用或同步冲突时不打断项目工作。
- 新建笔记的可读文件名主题部分和新建 Vault 的一级目录优先使用简体中文；固定结构文件名、项目内部目录、Schema 字段、枚举值和各类 ID 保持 ASCII 形式。不要因懒人包更新批量重命名已有笔记；任何正式移动或重命名仍需确认。
- 首次建库或关联仓库、修改共享状态或正式知识、接受决策、调整 schema 或同步设置、移动或删除笔记，以及 Git commit/push，继续遵守 Skill 既有确认边界。
- 只有懒人包 05/全部安装对话授权一次性 PC + SSH 服务器 Syncthing 引导；普通项目工作不得重配、启动或解除暂停。首次双向同步完成且两端本地引导状态都经核验为 `active` 后，才恢复自动维护。出现远端设备、目录非空、配置歧义、内容指纹不一致或不兼容时停止阶段转换，不影响无关工程任务。
- 内部链接必须使用 Vault 根相对、路径限定的 Wikilink；每条事实只保留一份权威记录，其他位置使用链接或短摘要。
<!-- codex-second-brain-managed:end -->
