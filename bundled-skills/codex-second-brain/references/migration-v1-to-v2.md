# Schema 1 → Schema 2 迁移

本参考只由 `repair` 的迁移子动作读取。当前懒人包锁定的最新受支持 Vault 格式是 Schema 2；“升级到最新版”只表示升级到锁文件声明的 Schema 2，不从远端追踪未知版本。它不是第九个模式，也不在懒人包安装阶段运行。迁移只改变 Vault 笔记结构；设备配置继续保持 Schema 2，且不会安装 Foam、同步工具、MCP 或执行 Git。

迁移不隐含根目录中文化。先按现有 Vault 结构识别路径；迁移输出必须统一使用用户确认的 `schema2-zh-cn` 或 `schema2-ascii` 布局。既有 ASCII 根目录明确吻合时默认保留原路径；任何根目录重命名都必须作为单独迁移差异展示并明确确认，不得因 Schema 1→2 升级而顺带改名。

## 完成条件

迁移只有同时满足以下条件才算完成：

- 根索引和 Projects、Areas、Knowledge、Resources 四个 collection index 存在且链接有效。
- 项目使用 `index.md`、独立 `status.md` 和原子化 `lessons/`。
- Knowledge 使用主题目录及 `index.md`；Resource 位于固定 source-type 子目录。
- 所有受管笔记拥有 Schema 2 通用元数据和唯一的类型前缀 UUIDv4。
- 内部链接是无前导 `/`、无 `.md` 的 Vault 根相对路径限定 Wikilink。
- Vault 本地模板保持权威，Syncthing/GitHub 职责和设备配置没有改变。
- 系统清单记录已确认的 `directory_layout`；所有输出路径均属于该布局且不存在平行根目录。
- 原输入已按确认的路径移除，活动 Vault 不同时保留两套结构；外部备份和迁移报告仍可用于回滚。

## 前置阻断条件

迁移前逐项确认：

1. 用户确认 Syncthing 在本机显示 up-to-date；目录或进程存在不能代替确认。
2. 用户确认其他设备、Obsidian、Codex worker、脚本和自动化没有写入该 Vault。
3. 递归检查 `.sync-conflict-*`、合并残留和双方版本文件；发现任何冲突立即停止。
4. 解析并验证默认外部路径：

   ```text
   <CodexHome>/second-brain/backups/<timestamp>/
   <CodexHome>/second-brain/migrations/<timestamp>/staging/
   ```

   两者不得位于 Vault、代码仓库或 Syncthing 同步目录内；不安全时让用户选择另一个外部路径。
5. 用户确认 dry-run 展示的全部新增、修改、移动、链接重写和旧路径移除范围。范围变化会使确认失效。

任一项无法确认时只报告阻断，不写 Vault。

## 必需的 dry-run

Dry-run 对 Vault 只读，可以向外部 staging 写报告和候选文件。它必须输出：

- 输入快照的 Vault 相对路径、哈希和 schema/type 状态。
- 每个输入到目标路径、类型、稳定 ID、状态和关系字段的映射。
- 将创建的目录、索引、模板、schema 和系统清单。
- 每个内部链接的旧目标、新目标和无法唯一解析的歧义。
- 定制模板差异、路径碰撞、重复 ID、未知状态、缺失标题/日期及其他待决项。
- 新建、修改、移动和移除的精确文件清单，以及 backup/staging 路径。

映射写入外部 `migration-map.json`，使用 Vault 相对路径，不把设备绝对路径写回 Vault。出现任何歧义时标记为阻断，不生成“最可能”的结果。

## 固定映射规则

### 目录与内容

| Schema 1 | Schema 2 | 处理规则 |
| --- | --- | --- |
| 缺失 Vault 首页 | `index.md` | 创建 root index，必须链接四个 collection index，可另链接系统清单。已有首页先展示差异。 |
| 缺失四个 collection index | 原路径 `index.md` | 只创建缺失项，不覆盖已有文件。 |
| 项目 `overview.md` | 项目 `index.md` | 保留项目身份、远端、知识范围和正文；生命周期状态移入 `status.md`。 |
| 项目 `status.md` | 原路径 | 转成 `project-status`，保存生命周期、目标、进度、阻塞和下一步。 |
| 项目 `lessons.md` | `lessons/<les-UUID>-历史经验待整理.md` | 有内容时原样保存为一条 `candidate` Lesson，并注明迁移来源；不自动按标题拆分。空模板只在备份后移除。 |
| Area 平铺文件 `<area>.md` | 当前布局 `Areas/<area>/index.md` | 保留正文并补 Area 元数据；已有目标不同则阻断。 |
| Knowledge 平铺文件 | 当前布局 `Knowledge/general/<kn-UUID>-<中文主题>.md` | 不猜主题；已有主题目录保留，并为缺失主题创建 `index.md`。 |
| Resource | 当前布局 `Resources/<source-type>/<res-UUID>-<中文主题>.md` | 只有旧元数据明确时保留分类，否则进入 `other`。 |
| Daily | 当前布局 `Daily/<year>/<YYYY-MM-DD>.md` | 只按明确日期归档到年份目录，不改写正文。 |
| Decision/Experiment/Session/Inbox | 对应 Schema 2 路径 | 保留正文，补元数据；正式原子文件名加入稳定 ID，Session/Inbox 保留设备独立命名。 |
| Vault 模板/schema | 当前布局 `System/templates/`、`System/schemas/` | 比较定制内容，只有确认后升级；不得用内置资产覆盖用户模板。 |

旧 `lessons.md` 可能包含多个主题，但迁移不做语义猜分。迁移后的 legacy Lesson 明确标记“待人工拆分”；以后由 `promote` 或 `repair` 在逐条复核后原子化。

### 元数据与状态

1. 已有合法 Schema 2 ID 保持不变；缺失、重复或格式错误时，在 `migration-map.json` 生成新的类型前缀 UUIDv4。重跑必须复用该映射。
2. 保留稳定 `project_id` 和规范化 `repository_urls`；它们不是笔记 UUID。所有项目关系继续引用同一 `project_id`。
3. `title` 优先取明确 frontmatter，其次取唯一一级标题；冲突或缺失时阻断。
4. 保留可信 ISO 日期。缺失或矛盾时要求用户决定，不用文件系统时间猜测。
5. 单数 `alias` 可以无歧义转换为 `aliases` 数组；`alias` 与 `aliases` 同时存在且不同则阻断。
6. 项目入口的旧 `status` 移入 `status.md`，且只能是 `active`、`paused`、`completed`、`archived`。
7. Lesson 迁移为 `candidate`。旧 Knowledge 完全缺少状态时使用保守的 `candidate`；已有但不属于 Schema 2 的状态则阻断。Decision、Experiment、Inbox 也只保留允许状态，未知值不从语气推断。
8. 未知自定义字段能原样保留时列入计划；需要改名、删除或推断时单独确认。

### 链接重写

1. 解析 Wikilink 和可识别的 Markdown 内部文件链接；不修改代码块、附件二进制、HTTPS URL 或纯文本示例。
2. 根据映射把目标改成 Vault 根相对路径，移除前导 `/`、`./`、`.md`，保留原显示别名。
3. `overview` 链接指向项目 `index`；聚合 lessons 链接指向 legacy Lesson。以后拆分时再经确认重写为具体原子 Lesson。
4. 同名目标、一个旧链接对应多个候选或目标不存在时阻断，不选择第一个、最新或最相似项。
5. 同样重写 frontmatter 中的内部链接；YAML Wikilink加引号。

## 应用、验证与回滚

用户确认完整 dry-run 后，按一个迁移批次执行：

1. 把所有将修改、移动或移除的原文件复制到外部 backup，并记录哈希；验证备份可读。
2. 在 staging 生成全部 Schema 2 输出、迁移映射和操作清单，完成元数据、ID、路径和链接检查。
3. 再次确认 no writers，重新读取输入；任何哈希变化都会返回 dry-run。
4. 按操作清单创建新路径、写入转换结果、更新链接并移除已迁移旧路径。不得覆盖计划外文件。
5. 对活动 Vault 运行完整健康检查，并确认系统清单已是 Schema 2、设备配置和同步/备份职责未变。
6. 只有全部检查通过后才记录迁移完成。任何一步失败都停止后续操作，删除本批次新建且未被外部修改的文件，并从 backup 恢复所有已改动原文件；保留失败报告、backup 和 staging。

如果无法证明自动回滚不会覆盖迁移期间的人工修改，保留双方版本并停止，不能声称已恢复或已完成。迁移完成后再次确认 Syncthing up-to-date；Git commit/push 仍需用户单独要求和确认。

## 验证与幂等性

- 受管笔记的通用字段完整，ID 前缀、UUIDv4 和唯一性正确。
- 目录、四个 collection index、项目入口/状态、Topic、Resource source-type 和原子内容可达。
- 没有前导 `/`、裸 basename、`.md`、相对路径、路径穿越、断链或歧义链接。
- 项目入口没有生命周期 `status`；`status.md` 有合法状态；Daily 未被自动重写。
- `aliases` 为数组，未遗留单数 `alias`；自定义模板和未确认字段没有被覆盖。
- Session/Inbox 仍设备独立；配置仍为 Schema 2、Syncthing 主同步、GitHub 人工备份。
- 已完成的输入再次 dry-run 返回 no-op。目标存在且内容相同则跳过；内容不同、哈希变化或映射不唯一时阻断。
- `migration-map.json` 长期保存输入哈希、目标、ID、链接映射和应用结果；相同输入和映射必须生成相同输出，不重复生成 ID。
