# Codex Second Brain Schema 2

本 Schema 使用一个 Obsidian Markdown Vault。`foam-inspired` 只表示借鉴单一工作区、原子笔记、索引和 Wikilink，不表示安装 Foam 或任何扩展。

完成 setup 后，Vault 内的 `90-System/templates/` 是模板权威，`90-System/schemas/schema-v2.md` 与 `90-System/second-brain.md` 记录当前约定。内置 assets 只用于 bootstrap、repair 或 fallback，不得覆盖已有笔记或定制模板。

## 目录

```text
<Vault>/
├─ index.md
├─ 00-Inbox/
│  ├─ <year>/<month>/<timestamp>-<device-short>-<slug>.md
│  └─ weekly-review-<year>-W<week>-<device-short>.md
├─ 10-Projects/
│  ├─ index.md
│  └─ <project-id>/
│     ├─ index.md
│     ├─ status.md
│     ├─ sessions/<year>/<timestamp>-<device-short>-<id8>.md
│     ├─ decisions/<decision-id>-<slug>.md
│     ├─ experiments/<experiment-id>-<slug>.md
│     └─ lessons/<lesson-id>-<slug>.md
├─ 20-Areas/index.md 与 <area-id>/index.md
├─ 30-Knowledge/index.md 与 <topic-id>/index.md、<knowledge-id>-<slug>.md
├─ 40-Resources/index.md 与 <source-type>/<resource-id>-<slug>.md
├─ 50-Daily/<year>/<YYYY-MM-DD>.md
├─ 60-Archive/
├─ 90-System/second-brain.md、schemas/、templates/
└─ attachments/
```

`source-type` 只能是 `web`、`paper`、`book`、`repository` 或 `other`。

## 模板映射

| 模板 | 默认位置 |
| --- | --- |
| `root-index.md` | `index.md` |
| `collection-index.md` | 四个顶层集合的 `index.md` |
| `project-index.md` | `10-Projects/<project-id>/index.md` |
| `project-status.md` | `10-Projects/<project-id>/status.md` |
| `session.md` | 项目 `sessions/<year>/` |
| `decision.md` | 项目 `decisions/` |
| `experiment.md` | 项目 `experiments/` |
| `lesson.md` | 项目 `lessons/` |
| `area-index.md` | `20-Areas/<area-id>/index.md` |
| `topic-index.md` | `30-Knowledge/<topic-id>/index.md` |
| `knowledge.md` | `30-Knowledge/<topic-id>/` |
| `resource.md` | `40-Resources/<source-type>/` |
| `inbox-note.md` | `00-Inbox/<year>/<month>/` |
| `daily.md` | `50-Daily/<year>/` |
| `weekly-review.md` | `00-Inbox/weekly-review-<year>-W<week>-<device-short>.md` |
| `system-manifest.md` | `90-System/second-brain.md` |

## 通用 frontmatter

每个受管笔记至少包含：

```yaml
schema_version: 2
id: "<type-prefix>-<uuid-v4>"
title: "人类可读标题"
type: "<note-type>"
created: "<ISO-8601>"
updated: "<ISO-8601>"
```

ID 小写且不可变。UUID 使用标准 v4 格式。所有双花括号占位符在落盘前都必须替换；不能把占位符写入真实笔记。

| `type` | 前缀 | 条件字段 | 状态 |
| --- | --- | --- | --- |
| `root-index` | `root` | 无 | 无 |
| `collection-index` | `col` | `collection_id`、`collection_path` | 无 |
| `project` | `prj` | `project_id`、`repository_urls`、`knowledge_scopes` | 无 |
| `project-status` | `pst` | `project_id` | `active`、`paused`、`completed`、`archived` |
| `session` | `ssn` | `project_id`、`device_id` | 无 |
| `decision` | `dec` | `project_id` | `proposed`、`accepted`、`superseded` |
| `experiment` | `exp` | `project_id` | `planned`、`running`、`completed`、`inconclusive` |
| `lesson` | `les` | `project_id` | `candidate`、`retained`、`promoted`、`archived` |
| `area-index` | `area` | `area_id` | 无 |
| `topic-index` | `topic` | `topic_id` | 无 |
| `knowledge` | `kn` | `topic_id` | `candidate`、`verified`、`deprecated` |
| `resource` | `res` | `source_type`、`sources` | 无 |
| `inbox` | `in` | 可空 `project_id`、`device_id` | `unprocessed`、`processed`、`archived` |
| `daily` | `day` | `date` | 无 |
| `weekly-review` | `week` | `week`、`device_id` | 无 |
| `second-brain-manifest` | `sys` | 无 | 无 |

`aliases`、`tags`、`sources`、`derived_from`、`supersedes` 都是数组。使用 `aliases`，不得使用单数 `alias`。`sources` 可以包含 HTTPS URL 或资源 Wikilink；关系字段中的 Wikilink 必须加引号。

## 链接与权威位置

内部链接使用无前导 `/`、无 `.md` 的 Vault 根相对路径限定 Wikilink：

```markdown
[[10-Projects/{{PROJECT_ID}}/status|项目状态]]
[[30-Knowledge/{{TOPIC_ID}}/{{KNOWLEDGE_FILENAME}}|知识笔记]]
[[40-Resources/{{SOURCE_TYPE}}/{{RESOURCE_FILENAME}}|资源笔记]]
```

不使用 `[[index]]`、`[[status]]` 等裸 basename，不使用 `./` 或 `../`。YAML 中写成 `"[[path|标题]]"`。

项目 `index.md` 管身份、远端、知识范围和导航；`status.md` 管生命周期、目标、进度、阻塞和下一步。Session 管工作事实，Daily 只做人工作日导航，Knowledge 管跨项目权威知识，Area/Topic/Collection/Root index 只管边界与导航。相同正文不得复制到多个位置。
