# Codex Second Brain Schema 2

本 Schema 使用一个 Obsidian Markdown Vault。`foam-inspired` 只表示借鉴单一工作区、原子笔记、索引和 Wikilink，不表示安装 Foam 或任何扩展。

完成 setup 后，Vault 内所选布局的 `{{PATH_SYSTEM}}/templates/` 是模板权威，`{{PATH_SYSTEM}}/schemas/schema-v2.md` 与 `{{PATH_SYSTEM}}/second-brain.md` 记录当前约定。内置 assets 只用于 bootstrap、repair 或 fallback，不得覆盖已有笔记或定制模板。

## 目录

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
├─ 20-领域/index.md 与 <area-id>/index.md
├─ 30-知识/index.md 与 <topic-id>/index.md、<knowledge-id>-<中文主题>.md
├─ 40-资源/index.md 与 <source-type>/<resource-id>-<中文主题>.md
├─ 50-日记/<year>/<YYYY-MM-DD>.md
├─ 60-归档/
├─ 90-系统/second-brain.md、schemas/、templates/
└─ 附件/
```

`source-type` 只能是 `web`、`paper`、`book`、`repository` 或 `other`。

## 目录布局与兼容

Schema 2 内容格式不变；目录布局使用独立标识 `schema2-zh-cn` 或 `schema2-ascii`，在系统清单 frontmatter 的 `directory_layout` 中记录。新建 Vault 默认采用 `schema2-zh-cn`，保留数字前缀以稳定排序。已存在的 `schema2-ascii` Vault 继续使用原路径；安装或升级不迁移、不改名，也不创建平行中文目录。

Vault 外层文件夹名不属于 Schema 2 或 `directory_layout`。新建 PC 主 Vault 默认建议使用中文外层目录名 `第二大脑`，完整路径由用户选定并确认；服务器镜像的绝对路径单独确认。已有 Vault 的外层名称不因安装或更新而更改；显式改名是独立路径迁移，需先停止相关写入/同步并核对两端配置与其他路径引用。

| 逻辑目录 | 新建中文布局 `schema2-zh-cn` | 既有兼容布局 `schema2-ascii` |
| --- | --- | --- |
| Inbox | `00-收件箱` | `00-Inbox` |
| Projects | `10-项目` | `10-Projects` |
| Areas | `20-领域` | `20-Areas` |
| Knowledge | `30-知识` | `30-Knowledge` |
| Resources | `40-资源` | `40-Resources` |
| Daily | `50-日记` | `50-Daily` |
| Archive | `60-归档` | `60-Archive` |
| System | `90-系统` | `90-System` |
| Attachments | `附件` | `attachments` |

模板路径变量按下列逻辑角色映射到所选布局的目录名：`{{PATH_INBOX}}`→Inbox、`{{PATH_PROJECTS}}`→Projects、`{{PATH_AREAS}}`→Areas、`{{PATH_KNOWLEDGE}}`→Knowledge、`{{PATH_RESOURCES}}`→Resources、`{{PATH_DAILY}}`→Daily、`{{PATH_ARCHIVE}}`→Archive、`{{PATH_SYSTEM}}`→System、`{{PATH_ATTACHMENTS}}`→Attachments。变量只存在于随包资产中；生成到 Vault 前须替换为表中实际路径。

项目内部的 `sessions/`、`decisions/`、`experiments/`、`lessons/`，System 下的 `schemas/`、`templates/`，以及 `index.md`、`status.md` 等固定机器路径继续使用 ASCII。一个 Vault 只能使用一种完整布局。

### 布局识别规则

- 先读系统清单中的 `directory_layout`，并核对其对应的 Schema 路径与根目录；声明与实际目录不符时停止相关写入。
- Vault 没有 `directory_layout` 时，只有在某一布局的 `schemas/schema-v2.md` 明确存在、其系统入口与目录映射一致、且另一布局入口不存在时，才可只读识别为该布局；不得为识别而回写标记。
- 只有全新空 Vault 才在用户确认初始化后默认采用 `schema2-zh-cn`；已有 Vault 即使缺少部分结构，也沿用已确认/识别的布局。非空未知布局停止并报告。
- `附件` 是新建中文布局建议的附件目录名；实际附件保存位置以 `.obsidian/app.json` 为准。已有设置需保留，不自动修改 `.obsidian` 或移动附件。
- 同时存在中英文系统入口、根目录混合、目录与标记冲突，或非空 Vault 无法明确归类时，报告歧义并停止创建、链接和笔记写入；不得猜测、合并或自动修复。
- 所有逻辑路径（Inbox、Projects、Areas、Knowledge、Resources、Daily、Archive、System、Attachments）都必须从选定布局解析。下文模板中的 `{{PATH_*}}` 是生成时变量，写入 Vault 前必须替换为所选布局的实际目录名；不得把占位符留在 Wikilink 或文件路径中。
- 双机共享同一个 Vault 时，各设备上的 Codex 规则都必须识别该布局；不同绝对 Vault 路径不影响目录布局，但不能让旧版写入者与中文布局混用。

## 文件名约定

- 新建笔记文件名中的可读主题部分优先使用简体中文，例如 `les-<UUID>-算子精度边界.md`；Session 和 Inbox 在时间戳、设备短 ID 等唯一标识后追加中文摘要/主题。
- 周整理草案使用 `每周整理-<year>-W<week>-<device-short>.md`；frontmatter 的 `type: weekly-review` 保持不变。
- `project_id`、`area_id`、`topic_id`、Schema 字段与枚举值、项目内部目录名和 `index.md`/`status.md` 等结构文件名保持 ASCII。顶层目录按已选布局使用中文或兼容 ASCII 名称。可读主题使用 Unicode NFC，只保留汉字、ASCII 字母/数字和连字符；空格及其他标点替换为连字符，并保持简短。
- 既有文件名不会因安装或升级被批量重命名。需要改名时先展示受影响的 Wikilink 和索引差异，并取得确认。

## 模板映射

| 模板 | 默认位置 |
| --- | --- |
| `root-index.md` | `index.md` |
| `collection-index.md` | 四个顶层集合的 `index.md` |
| `project-index.md` | `{{PATH_PROJECTS}}/<project-id>/index.md` |
| `project-status.md` | `{{PATH_PROJECTS}}/<project-id>/status.md` |
| `session.md` | 项目 `sessions/<year>/` |
| `decision.md` | 项目 `decisions/` |
| `experiment.md` | 项目 `experiments/` |
| `lesson.md` | 项目 `lessons/` |
| `area-index.md` | `{{PATH_AREAS}}/<area-id>/index.md` |
| `topic-index.md` | `{{PATH_KNOWLEDGE}}/<topic-id>/index.md` |
| `knowledge.md` | `{{PATH_KNOWLEDGE}}/<topic-id>/` |
| `resource.md` | `{{PATH_RESOURCES}}/<source-type>/` |
| `inbox-note.md` | `{{PATH_INBOX}}/<year>/<month>/` |
| `daily.md` | `{{PATH_DAILY}}/<year>/` |
| `weekly-review.md` | `{{PATH_INBOX}}/每周整理-<year>-W<week>-<device-short>.md` |
| `system-manifest.md` | `{{PATH_SYSTEM}}/second-brain.md` |

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
| `second-brain-manifest` | `sys` | `directory_layout` (`schema2-zh-cn` 或 `schema2-ascii`) | 无 |

`aliases`、`tags`、`sources`、`derived_from`、`supersedes` 都是数组。使用 `aliases`，不得使用单数 `alias`。`sources` 可以包含 HTTPS URL 或资源 Wikilink；关系字段中的 Wikilink 必须加引号。

## 链接与权威位置

内部链接使用无前导 `/`、无 `.md` 的 Vault 根相对路径限定 Wikilink：

```markdown
[[{{PATH_PROJECTS}}/{{PROJECT_ID}}/status|项目状态]]
[[{{PATH_KNOWLEDGE}}/{{TOPIC_ID}}/{{KNOWLEDGE_FILENAME}}|知识笔记]]
[[{{PATH_RESOURCES}}/{{SOURCE_TYPE}}/{{RESOURCE_FILENAME}}|资源笔记]]
```

不使用 `[[index]]`、`[[status]]` 等裸 basename，不使用 `./` 或 `../`。YAML 中写成 `"[[path|标题]]"`。

项目 `index.md` 管身份、远端、知识范围和导航；`status.md` 管生命周期、目标、进度、阻塞和下一步。Session 管工作事实，Daily 只做人工作日导航，Knowledge 管跨项目权威知识，Area/Topic/Collection/Root index 只管边界与导航。相同正文不得复制到多个位置。
