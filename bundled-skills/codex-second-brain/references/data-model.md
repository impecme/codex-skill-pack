# 数据模型（Vault Schema 2）

执行 `setup`、`link`、`startup`、`promote` 或 `repair` 的结构检查时读取本参考。涉及链接语法和健康检查时读取 [linking-and-health.md](linking-and-health.md)；涉及写入、同步、模板或 Git 时读取 [safety-and-sync.md](safety-and-sync.md)。

## 设计边界

- 只维护一个 Obsidian Vault；它是项目上下文和可复用知识的唯一事实源。
- Foam 只提供单一工作区、原子 Markdown、索引和 Wikilink 等组织思想；不得安装 Foam、Foam CLI、VS Code 扩展或 MCP。
- 顶层目录表达内容职责，不等于用户要手工执行的流程。新建 Vault 默认使用中文顶层目录，既有 ASCII 布局继续兼容；新笔记文件名中可读的主题部分、显示标题和 Wikilink 别名优先使用简体中文。固定内部目录、机器字段、枚举值和各类 ID 保持 ASCII。
- `index.md` 只负责身份、边界和导航；事实正文只保存在对应的唯一权威笔记。
- `schema_version` 是 Vault 笔记格式；设备配置的 `schemaVersion` 独立保持为 `2`。

## Vault 目录结构

只创建缺失目录。重命名、移动或删除现有内容必须按 [safety-and-sync.md](safety-and-sync.md) 展示差异并确认。

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
│  └─ <topic-id>/
│     ├─ index.md
│     └─ <knowledge-id>-<中文主题>.md
├─ 40-资源/
│  ├─ index.md
│  └─ <web|paper|book|repository|other>/<resource-id>-<中文主题>.md
├─ 50-日记/<year>/<YYYY-MM-DD>.md
├─ 60-归档/
├─ 90-系统/
│  ├─ second-brain.md
│  ├─ schemas/schema-v2.md
│  └─ templates/<template>.md
└─ 附件/
```

### 目录布局解析

Vault Schema 仍为 2；目录布局用系统清单中的 `directory_layout` 独立标识：新建 Vault 使用 `schema2-zh-cn`，既有布局使用 `schema2-ascii`。映射表和冲突处理以 [Schema 2 资产](../assets/vault-schemas/schema-v2.md#目录布局与兼容) 为唯一权威。

每次读写前读取系统清单和对应 schema 路径，解析逻辑目录名 `Inbox`、`Projects`、`Areas`、`Knowledge`、`Resources`、`Daily`、`Archive`、`System`、`Attachments`。旧 Vault 缺少布局标识时只按 Schema 资产中的规则只读识别；不补写标记。新建时默认中文布局。双重入口、混合目录、声明与实际路径冲突、或非空 Vault 不能明确识别时停止相关写入，不猜测、不生成第二套集合。

内置模板中的 `{{PATH_*}}` 是逻辑路径变量；创建模板或笔记时必须按该 Vault 的布局替换为实际目录名，不能把变量原样写进 Wikilink、索引、frontmatter 或文件路径。

根 `index.md` 链接四个 collection index：`{{PATH_PROJECTS}}/index.md`、`{{PATH_AREAS}}/index.md`、`{{PATH_KNOWLEDGE}}/index.md` 和 `{{PATH_RESOURCES}}/index.md`。项目、Area 和 Knowledge 主题的 `index.md` 再维护局部导航。

`project_id` 是由规范化 Git 远端生成的稳定 ASCII 目录键，通常形如 `github.com__owner__repository`；它不是笔记自身的 UUID `id`。没有 Git 远端时必须让用户确认一个稳定 ID。`area_id`、`topic_id`、文件名前缀中的类型标识和 UUID 保持 ASCII；人类可读的文件名主题部分使用安全的简体中文。

### 单一权威位置

| 内容 | 权威位置 |
| --- | --- |
| 项目身份、仓库映射、知识范围和项目导航 | 项目 `index.md` |
| 项目生命周期、当前目标、进度、阻塞和下一步 | `status.md` |
| 一次任务的事实和验证结果 | `sessions/` |
| 已接受的项目决策 | `decisions/` |
| 可复现实验 | `experiments/` |
| 项目内可复用经验 | 原子化 `lessons/` |
| 跨项目权威知识 | 逻辑目录 `Knowledge/` 下的原子 Knowledge |
| 领域、主题和集合导航 | 对应 `index.md` |
| 外部资料摘要和出处 | 逻辑目录 `Resources/` |
| 人工时间导航 | 逻辑目录 `Daily/` |

同一正文只保留一份；其他位置只使用路径限定链接或短摘要。

## 通用元数据

所有由本 Skill 创建或维护的 Schema 2 Markdown 至少包含：

```yaml
---
schema_version: 2
id: "kn-7f3c9d46-9b7a-4a28-8f17-2d4b71b0c5e1"
title: "示例知识"
type: knowledge
created: "2026-10-03"
updated: "2026-10-03"
---
```

- `id` 是不可变的小写 `<type-prefix>-<UUIDv4>`。UUID 使用 `8-4-4-4-12` 格式，第三段以 `4` 开头，第四段以 `8`、`9`、`a` 或 `b` 开头。
- `title` 是人类可读标题；frontmatter 与首个一级标题冲突时停止并报告。
- `created`、`updated` 使用 ISO 8601。长期笔记可以只写日期；Session、Inbox 等事件笔记使用带时区的时间戳。
- `aliases`、`tags` 是可选字符串数组；不得使用单数 `alias`。
- `sources` 可保存 HTTPS URL 或资源笔记 Wikilink；`derived_from`、`supersedes` 保存路径限定 Wikilink。YAML 中的 Wikilink 必须加引号。
- 只写适用字段，不用占位字符串冒充已经确认的值。文件移动、改名或标题变化时 `id` 保持不变。

### 类型、前缀、条件字段与状态

| `type` | 前缀 | 条件字段 | 允许的 `status` |
| --- | --- | --- | --- |
| `root-index` | `root` | 无 | 不使用 |
| `collection-index` | `col` | `collection_id`、`collection_path` | 不使用 |
| `project` | `prj` | `project_id`、`repository_urls`、`knowledge_scopes` | 不使用 |
| `project-status` | `pst` | `project_id` | `active`、`paused`、`completed`、`archived` |
| `session` | `ssn` | `project_id`、`device_id` | 不使用 |
| `decision` | `dec` | `project_id` | `proposed`、`accepted`、`superseded` |
| `experiment` | `exp` | `project_id` | `planned`、`running`、`completed`、`inconclusive` |
| `lesson` | `les` | `project_id` | `candidate`、`retained`、`promoted`、`archived` |
| `area-index` | `area` | `area_id` | 不使用 |
| `topic-index` | `topic` | `topic_id` | 不使用 |
| `knowledge` | `kn` | `topic_id`；按需使用来源和关系字段 | `candidate`、`verified`、`deprecated` |
| `resource` | `res` | `source_type`、`sources` | 不使用 |
| `inbox` | `in` | 可空 `project_id`、`device_id` | `unprocessed`、`processed`、`archived` |
| `daily` | `day` | `date` | 不使用 |
| `weekly-review` | `week` | `week`、`device_id` | 不使用 |
| `second-brain-manifest` | `sys` | `directory_layout` | 不使用 |

`source_type` 只能是 `web`、`paper`、`book`、`repository` 或 `other`。项目状态只存在于 `project-status`；项目 `index.md` 不复制生命周期状态。

### 文件名规则

- 新建 Decision、Experiment、Lesson、Knowledge 和 Resource 使用 `<完整笔记-id>-<中文主题>.md`；主题从标题提炼，避免冗长。
- Session 使用 `<UTC timestamp>-<device-short>-<id8>-<中文摘要>.md`，Inbox 使用 `<UTC timestamp>-<device-short>-<中文主题>.md`；完整 ID 保存在 frontmatter。
- Weekly Review 文件使用 `每周整理-<year>-W<week>-<device-short>.md`；frontmatter 的 `type: weekly-review` 等 Schema 枚举值不变。
- 文件名主题部分优先用简体中文，可保留必要的 ASCII 技术缩写；统一为 Unicode NFC，只使用汉字、ASCII 字母/数字和连字符，其他空格或标点替换为连字符，并保持简短。既有文件名保持不变；重命名和链接更新必须单独确认。
- `device-short` 来自稳定 `deviceId` 的安全短表示；创建前仍须检查目标不存在，碰撞时生成新的 UUID，不覆盖。
- `index.md`、`status.md` 和 Daily 使用固定文件名，但仍拥有独立 UUID `id`。

## 项目识别

1. 只读获取 Git 远端，不修改 Git 配置。
2. 将常见 SSH 和 HTTPS 地址规范化为 `https://<lowercase-host>/<lowercase-owner>/<lowercase-repository>`，移除末尾 `.git` 或 `/`。
3. 优先使用 `origin`；没有时检查其他远端。多个合理候选必须询问用户。
4. 在 `{{PATH_PROJECTS}}/*/index.md` 的 `repository_urls` 中做规范化后的精确匹配。
5. 唯一匹配时使用其 `project_id`；多个匹配、重复 ID 或 URL 与目录冲突时停止。
6. 没有匹配时展示候选和新建方案；用户确认后才创建项目目录、`index.md`、`status.md` 和 collection index 差异。
7. 远端改名时保留旧 URL；经确认后追加新 URL。不得根据本地目录名、相似标题或 fork 关系静默合并项目。

## 自动记录与 Daily

- 一个连续任务默认最多一条 Session；checkpoint 和 shutdown 重新读取并追加同一文件。无法可靠确认时新建唯一 Session，不覆盖旧文件。
- 未关联仓库时不得猜建项目目录；必须保留的证据写入 `project_id: null` 的设备独立 Inbox。
- Daily 是人工时间导航。Codex 可以按需只读，但不得在 `startup`、`checkpoint` 或 `shutdown` 中自动创建或改写 Daily。

## 模板与清单

- `<Vault>/{{PATH_SYSTEM}}/templates/` 是当前 Vault 的权威模板目录；允许用户定制。
- `<Vault>/{{PATH_SYSTEM}}/schemas/schema-v2.md` 与 `{{PATH_SYSTEM}}/second-brain.md` 记录当前 schema 和组织约定。
- 内置 `assets/vault-templates/` 与 `assets/vault-schemas/` 只用于 bootstrap、repair 或 fallback，不能静默覆盖 Vault 本地版本。
- 缺少模板时，Session/Inbox 可临时使用内置 Schema 2 模板并报告 repair 待办；共享或正式笔记必须先展示模板恢复差异并确认。
- 模板升级只展示差异。若 Vault 模板已定制，保留本地版本，等待用户手动合并。
