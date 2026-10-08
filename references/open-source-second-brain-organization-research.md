# 高 Star 开源第二大脑组织形式调研

> 核验日期：2026-10-03
> 范围：个人知识管理、第二大脑和长期 Markdown 知识库的组织方式
> 来源原则：只使用项目官方 GitHub 仓库、GitHub API 和项目官方文档

## 结论

当前“收集层 → 项目层 → 长期知识层”的逻辑不需要推翻。最适合本项目的不是完整复制某一个
高 Star 应用，而是组合多个成熟项目中已经得到验证的做法：

- 使用 Memos 和 Logseq 的低摩擦、时间线式收集方式。
- 使用 Foam 的单一工作区、原子 Markdown、链接、反向链接和模板方式作为主体。
- 使用 SiYuan 和 Trilium 的稳定身份、属性和显式关系思想，但不采用它们的数据库存储格式。
- 使用 Dendron 的渐进式结构和轻量 schema，不复制它的多 Vault 模型。
- 使用 TIL 仓库的短小知识条目和主题索引方式维护长期知识。

Star 数反映社区采用度，但不能单独决定适配性。Memos、SiYuan 和 Logseq 的 Star 很高，分别擅长
快速收集、块级知识和日志式知识图谱；与当前“Obsidian + 标准 Markdown + Syncthing”最接近的
仍然是 Star 较低但模型最匹配的 Foam。

## 比较标准

对每个项目同时考察：

1. GitHub Star 快照和维护状态。
2. 是否以本地文件和标准 Markdown 为中心。
3. 是否适合一个知识库容纳多个代码项目。
4. 是否提供低摩擦收集、稳定身份、来源追踪和知识晋升思路。
5. 是否适合 Syncthing 多设备同步和 GitHub 手动备份。
6. 是否会引入数据库、服务端或专用格式等额外事实源。

## 候选对比

Star 数是 2026-10-03 的查询快照。Memos、SiYuan 和 Logseq 使用 GitHub API 精确值；其余项目
使用 GitHub 仓库页显示的四舍五入值，因此以“约”标记。

| 项目 | Star 快照 | 状态与许可 | 主要组织模型 | 可借鉴内容 | 不适合直接照搬的部分 |
| --- | ---: | --- | --- | --- | --- |
| [Memos](https://github.com/usememos/memos) | [63,473](https://api.github.com/repos/usememos/memos) | 活跃，MIT | 无标题快速记录、时间线、搜索、标签和日期 | Inbox 应允许先记录后分类；采集内容保留来源链接 | 它主要解决收集，不足以独立承担项目状态、决策和长期知识治理 |
| [SiYuan](https://github.com/siyuan-note/siyuan) | [46,612](https://api.github.com/repos/siyuan-note/siyuan) | 活跃，AGPL-3.0 | 块级 ID、双向链接、自定义属性和查询 | 给正式笔记稳定 ID；用属性表达状态、来源和关系 | 工作区使用 `.sy` JSON；官方明确警告第三方同步盘可能导致损坏，不适合替代当前 Markdown + Syncthing 存储 |
| [Logseq](https://github.com/logseq/logseq) | [45,115](https://api.github.com/repos/logseq/logseq) | 活跃，AGPL-3.0 | Journal-first、块、页面引用、标签和属性 | 每日入口、快速捕获、属性化记录、从日志链接到主题 | 新 DB Graph 使用 SQLite；不应把数据库或块级复杂度引入当前 Vault |
| [TriliumNext](https://github.com/TriliumNext/Trilium) | 约 38.2k | 活跃，AGPL-3.0 | 笔记树、克隆、属性、关系和模板 | 一个权威笔记可以从多个位置引用；不要复制同一知识正文 | 主要数据不是普通 Markdown 文件树，克隆和继承语义难以在 Obsidian 中原样复现 |
| [Foam](https://github.com/foambubble/foam) | 约 17.4k | 未归档，MIT | 单一工作区、原子 Markdown、wikilink、反向链接、Daily、模板 | 与当前方案最接近；适合作为文件和链接组织的主参考 | 工具本身不定义完整的项目状态、决策审批和知识晋升流程 |
| [jbranchaud/til](https://github.com/jbranchaud/til) | 约 14.1k | 持续更新，MIT | 按主题分类的大量短小、单一主题 Markdown | 长期知识保持原子化；用主题索引聚合，不写巨型综合笔记 | 只覆盖知识输出，不覆盖 Inbox、项目工作记忆或跨设备写入 |
| [Dendron](https://github.com/dendronhq/dendron) | 约 7.5k | **维护模式，活跃开发已停止**，Apache-2.0 | 点分层级、渐进式结构、schema、模板和重构 | schema 应是可选约束；结构随规模逐步增加 | 不应依赖已停止活跃开发的工具，也不需要复制其多 Vault 设计 |

### 关键第一方依据

- Memos 官方仓库将产品定义为按时间线记录短笔记，并通过搜索、标签或日期找回；官方 Web Clipper
  会把内容保存为带来源链接的 Markdown。[Memos 仓库](https://github.com/usememos/memos)
- SiYuan 官方说明支持块级引用、双向链接和自定义属性；同时说明文档保存在 `.sy` JSON 中，并明确
  不支持第三方同步盘，否则可能损坏数据。[SiYuan README](https://github.com/siyuan-note/siyuan#readme)
- Logseq 官方文档说明 Journal 自动按日期创建，页面和块可以携带属性、标签和引用。
  [Logseq DB 文档](https://github.com/logseq/docs/blob/master/db-version.md)
- Trilium 官方文档把笔记作为核心实体；笔记可以同时包含内容和子笔记，属性可以是普通键值或
  指向其他笔记的具名关系。[Notes](https://github.com/TriliumNext/Trilium/blob/main/docs/User%20Guide/User%20Guide/Basic%20Concepts%20and%20Features/Notes.md)、
  [Attributes](https://github.com/TriliumNext/Trilium/wiki/Attributes)
- Foam 官方仓库推荐一个工作区、单一主题的原子 Markdown、wikilink、反向链接、Daily 和模板，
  并说明 Obsidian Vault 通常已经可以作为 Foam 工作区。
  [Foam 仓库](https://github.com/foambubble/foam)
- Dendron 官方资料把层级定义为点分文件名，并把 schema 描述为知识的可选类型系统；其仓库同时
  明确标注只进入维护模式。[Dendron 功能](https://github.com/dendronhq/dendron-site/blob/master/vault/dendron.features.md)、
  [Dendron 仓库](https://github.com/dendronhq/dendron)
- TIL 仓库用主题分类管理超过一千条简短知识，证明“原子条目 + 主题索引 + Git 历史”可以长期扩展。
  [jbranchaud/til](https://github.com/jbranchaud/til)

## Foam 官方要点与采用边界

Foam 官方把它定义为建立在 VS Code 和 GitHub 之上的个人知识管理与分享系统，并明确推荐一个工作区、
原子化的 Markdown 文档和 `[[wikilinks]]`；它也提供反向链接、模板、属性和工作区 lint 等能力。这里采用的是
这些文件与链接组织原则，不是把 Foam 运行时加入懒人包。

- [创建第一个工作区](https://docs.foam.md/getting-started/first-workspace/) 推荐单一工作区，因为所有知识集中后更容易发现链接、维护和备份。
- [从 Obsidian 迁移](https://docs.foam.md/recipes/migrating-from-obsidian/) 说明 Obsidian Vault 大体已经是 Foam 工作区：两者都以目录中的普通 Markdown 文件保存笔记。
- [Wikilinks](https://docs.foam.md/features/wikilinks/) 区分全库 identifier link 与路径 link；Schema 2 选择 Vault 根相对的 `/` 路径限定形式，并省略 `.md`，避免同名笔记产生歧义。
- [Backlinks](https://docs.foam.md/features/backlinking/) 说明反向链接可以自动发现引用当前笔记的其他笔记；Schema 2 保留这种可发现性，但不要求额外数据库。
- [Templates](https://docs.foam.md/features/templates/) 支持用 Markdown 或 JavaScript 模板减少重复劳动；本项目只采用 Vault 本地 Markdown 模板，并让本地副本成为权威。
- [Note Properties](https://docs.foam.md/features/note-properties/) 以文件顶部 YAML front matter 表达类型、标题和标签；[Obsidian Properties](https://obsidian.md/help/properties) 也支持稳定的文本、列表、日期和 checkbox 属性，因此 Schema 2 只保留少量可移植字段。
- [Workspace Lint](https://docs.foam.md/tools/workspace-lint/) 可检查链接引用定义和标题，并可通过 `foam-cli` 或 VS Code 运行；这属于 Foam 工具链能力，不是本包的安装前提。

最终采用边界：采用单一 Vault、原子 Markdown、双向链接语义、路径限定 Wikilink、主题目录与 `index.md`、
模板和轻量 front matter；用项目 `index.md`、`status.md` 与 `lessons/` 原子笔记补足 Foam 不定义的项目状态和经验治理。
最终不采用 Foam 应用、Foam CLI、VS Code 扩展、Foam 的 GitHub 模板、插件或 MCP；不把图谱、lint 或 backlink
面板当作运行时依赖，也不以 Foam 替换 Obsidian、Syncthing 或 GitHub 私有人工备份。

## 对当前结构的判断

[当前数据模型](../bundled-skills/codex-second-brain/references/data-model.md)的核心方向正确：

- 一个主 Vault，避免不同项目和设备形成多个事实源。
- 项目通过规范化 Git 远端获得稳定 `project_id`。
- 项目状态、工作记录、决策、实验和可复用知识分开存放。
- 设备路径保存在 Vault 外部，不污染同步数据。

需要优化的不是层数，而是以下边界：

1. Inbox、Projects、Areas/Knowledge 表达内容成熟度；新建 Vault 使用中文目录名并保留数字前缀。
2. Resources 和 Daily 表达内容类型或入口，不是第四、第五层。
3. Archive 表达生命周期状态，System 和 Attachments 属于基础设施。
4. `Daily`、项目 Session 和 Inbox 目前可能重复记录同一内容。
5. 多设备同时追加同一个 Daily 或 `status.md` 容易产生 Syncthing 冲突。
6. 正式知识已有 `sources`，但仍缺少稳定笔记 ID、派生来源和替代关系。

## Schema 2 推荐组织形式

新建 Vault 使用中文顶层目录；既有 ASCII Vault 为兼容性保留原路径，不因升级迁移。把项目导航、项目状态和经验条目拆开，并让主题目录自带索引：

```text
<Vault>/
├─ index.md
├─ 00-收件箱/
│  ├─ <year>/<month>/<timestamp>-<device-short>-<中文主题>.md
│  └─ 每周整理-<year>-W<week>-<device-short>.md
├─ 10-项目/
│  ├─ index.md
│  └─ <project-id>/
│     ├─ index.md
│     ├─ status.md
│     ├─ sessions/<year>/<timestamp>-<device-short>-<id8>-<中文摘要>.md
│     ├─ decisions/<decision-id>-<中文主题>.md
│     ├─ experiments/<experiment-id>-<中文主题>.md
│     └─ lessons/<lesson-id>-<中文主题>.md
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
├─ 50-日记/
│  └─ <year>/YYYY-MM-DD.md
├─ 60-归档/
├─ 90-系统/
│  ├─ second-brain.md
│  ├─ schemas/schema-v2.md
│  └─ templates/
└─ 附件/
```

Skill 提供的 16 个模板只是首次建库的种子；写入 Vault 后，所选布局中的 `templates/` 和系统清单记录的 Schema 2 是该 Vault 的运行时约定；安装目录的 `assets/vault-schemas/`
只用于 bootstrap、repair 或 fallback。模板更新必须展示差异并确认，不从安装目录静默覆盖。

### 三层内容流（保留逻辑，不等于只允许三层目录）

```text
收集层                         项目层                         长期层
00-收件箱 / 50-日记  ───────> 10-项目  ───────────────> 20-领域 / 30-知识
      │                            │                              │
      └─ 丢弃或保留原始记录         └─ 项目专属内容留在项目内        └─ 经复核的唯一权威知识

40-资源 ────────────────────> 为任意层提供外部来源和证据
60-归档 / 90-系统 ──────────> 生命周期和系统支持，不参与知识晋升
```

### 单一权威位置

| 信息 | 唯一权威位置 |
| --- | --- |
| 项目身份、规范化远端和导航 | `10-项目/<project-id>/index.md` |
| 当前项目目标、进度、阻塞和下一步 | `10-项目/<project-id>/status.md` |
| 某次工作的事实和验证 | `10-项目/<project-id>/sessions/` |
| 可复现实验 | `10-项目/<project-id>/experiments/` |
| 已接受的项目决策 | `10-项目/<project-id>/decisions/` |
| 项目内尚未沉淀的经验 | `10-项目/<project-id>/lessons/<lesson-id>.md` |
| 跨项目复用的权威知识 | `30-知识/<topic>/<note-id>.md` |
| 主题导航和知识地图 | `30-知识/<topic>/index.md` |
| 领域导航和知识地图 | `20-领域/<area-id>/index.md` |
| 外部资料摘要和出处 | `40-资源/` |

同一正文不得在多个位置复制。Area、项目和 Daily 通过链接引用权威笔记，借鉴 Trilium 的“多处出现、
单一实体”思想，但保持普通 Markdown 实现。所有跨目录链接使用 Vault 根相对、路径限定 Wikilink，优先写成
新建中文 Vault 使用 `[[10-项目/<project-id>/status|项目状态]]`；既有 ASCII Vault 使用其既有目录路径。两者都不带前导 `/`，也不使用只依赖笔记 basename 的全库 identifier link。

## 元数据优化

不要引入复杂标签体系。由懒人包管理的正式笔记统一使用少量稳定字段：

```yaml
---
id: kn-7f3c9d46-9b7a-4a28-8f17-2d4b71b0c5e1
schema_version: 2
title: 示例知识
type: knowledge
status: verified
created: 2026-10-03
updated: 2026-10-03
project_id: null
sources: []
derived_from: []
supersedes: []
---
```

- `id`：稳定身份，文件移动或改名时保持不变。
- `type`：决定模板和校验规则。
- `status`：使用少量固定值，例如 `unprocessed`、`active`、`verified`、`deprecated`、`archived`。
- `sources`：外部证据。
- `derived_from`：从哪些 Session、实验、决策或资源沉淀而来。
- `supersedes`：新知识替代了哪些旧结论；旧笔记标记 `deprecated`，不静默删除。

只有适用的字段才写入，不要求所有临时笔记携带全部字段。

## 多设备冲突优化

结合 Syncthing 时，自动写入优先使用不可重名的追加式文件：

- Inbox：`<timestamp>-<device-id>-<中文主题>.md`。
- Session：`<timestamp>-<device-id>.md`。
- 实验和决策：创建后以追加和小范围修改为主。
- Codex 不应在多台设备上自动追加同一个 Daily 文件。
- `status.md`、Area 索引和正式 Knowledge 属于共享可变文件；写入前必须等待同步完成、重新读取并确认差异。

GitHub 作为备份时，建议只在指定设备维护 `.git` 并手动提交；Syncthing 同步知识内容，不同步
`.git`、设备级配置、工作区 UI 状态或冲突临时文件。

## 最终取舍

推荐采用“高 Star 项目的组合模型”，而不是增加更多层级：

1. **主体：Foam**——单一 Markdown 工作区、原子笔记和链接。
2. **收集：Memos + Logseq**——快速记录、时间入口、稍后整理。
3. **身份和关系：SiYuan + Trilium**——稳定 ID、属性、来源和一份权威正文。
4. **治理：Dendron**——渐进式 schema，不在一开始强迫所有内容高度结构化。
5. **长期知识：TIL**——短小、单主题、可按主题索引的知识条目。

因此 Schema 2 保留三层内容流和当前顶层目录，但把项目入口改为 `index.md`，把经验拆成
`lessons/` 下的原子笔记，并为每个主题提供 `index.md`；它同时固定单一 Vault、Syncthing 主同步、
GitHub 私有仓库人工备份、路径限定 Wikilink 和 Vault 本地模板权威。它不更换 Obsidian、不引入数据库，
也不安装 Foam、Foam CLI、VS Code 扩展或 MCP，更不为每个项目创建独立 Vault。
