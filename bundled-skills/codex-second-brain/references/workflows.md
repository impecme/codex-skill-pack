# 工作流（Schema 2）

这些模式是内部动作，不是用户必须执行的步骤。先定位当前动作，再按需读取 [data-model.md](data-model.md)、[linking-and-health.md](linking-and-health.md) 和 [safety-and-sync.md](safety-and-sync.md)。迁移是 `repair` 的子动作，不新增第九个模式。

## 初始化（`setup`）

1. 读取 `<CodexHome>/second-brain/config.json`。尚未配置时，让用户选择已有 Vault 或用于初始化的空目录；只支持一个主 Vault。
2. 写入前检查已有顶层路径、同名文件、明显同步冲突和 `.obsidian`。本 Skill 不安装或配置 Foam、Foam CLI、VS Code 扩展或 MCP。
3. 展示将创建的根 `index.md`、四个 collection index、必要目录、16 个 Vault 模板、`90-System/schemas/schema-v2.md`、系统清单、本机配置、同步/备份职责和可选周任务；首次初始化必须确认。
4. 只创建缺失内容。先使用 Vault 本地模板；首次建库从内置 Schema 2 assets 复制模板和 schema。已有模板、字段和正文不得覆盖，升级只展示差异。
5. 根索引必须链接 Projects、Areas、Knowledge、Resources 四个 collection index，也可以链接系统清单；项目、Area、Topic 和正式内容按需创建，不预先生成空知识笔记或 Daily index。
6. 设备配置保持 `schemaVersion: 2`、`syncMode: syncthing`、`backupMode: github-manual`。修改 Vault 路径、设备标签、备份角色、写入策略或自动化 ID 前展示差异；保留未知字段，不保存凭证。
7. 若本 Skill 由懒人包 05 安装流程调用，按 [syncthing-bootstrap.md](syncthing-bootstrap.md) 检查本机同步配置已完成；不得添加远端设备、解除暂停或传输 Vault。普通 setup 不安装、不重配 Syncthing，只确认所选目录对应已配置的主 Vault。本机是否为唯一 GitHub 人工备份设备仍按原流程确认；不初始化 Git，不执行 commit、pull 或 push。
8. 只有 `gitBackupDevice: true` 的唯一指定设备，在用户提供星期、当地时间和时区后，才创建一个调用 `weekly` 的原生周期任务。它只能写设备独立 Inbox 草案并执行只读健康检查。
9. 重新读取生成结果，运行只读健康检查，报告 Vault、Schema 2、模板权威位置、同步/备份职责和自动化 ID。原生自动化不可用时保持 ID 为 `null` 并返回手动提示词。

## 关联项目（`link`）

1. 读取设备配置并只读获取 Git 远端；按 [data-model.md](data-model.md) 规范化，不修改 Git 配置。
2. 在 `10-Projects/*/index.md` 的 `repository_urls` 中精确匹配。目录名、相似标题、fork 关系和本地路径都不能替代远端匹配。
3. 没有匹配时，展示候选、ASCII `project_id`、为项目索引和状态页分别生成的类型前缀 UUIDv4、待创建目录/文件及 collection index 差异；确认后才写入。
4. 确认关联已有项目时，只在确实缺少远端别名后提出追加差异。多个匹配、重复 ID、目标变化或同步冲突时停止。
5. 项目 `index.md` 只保存身份、远端、知识范围和导航；生命周期及当前目标、进度、阻塞、下一步都由 `status.md` 维护。
6. 完成后重新读取目标，确认当前远端只解析到一个 `project_id`。不得把 Vault 绝对路径写入代码仓库或生成项目侧关联文件。

## 开始工作（`startup`）

1. 每个会话首次对同一 Git 项目开展实质性工作时自动运行一次；已恢复过则不重复。
2. 解析设备配置并确认 Vault 可访问。配置缺失、Vault 暂不可达或有同步冲突时，不阻塞不依赖历史的工程工作；只有历史会影响正确性时才暂停。
3. 只读识别项目。未关联时准备一次性 `link` 方案，但不猜测项目、不在未确认时创建项目 Session。
4. 读取项目 `index.md`、`status.md`、最近 Session，以及 `knowledge_scopes` 明确列出的 Area/Topic index 和当前任务直接需要的已链接笔记；不得扫描整个 Vault。
5. 需要时间线背景时可只读最近 Daily；不得自动创建或修改 Daily。
6. 只读获取代码仓库状态，将目标、进展、阻塞和下一步用于当前任务。发现 schema 或链接问题时只生成 `repair` 报告。

## 阶段记录（`checkpoint`）

1. 只在长任务出现已验证、跨轮次仍有价值的成果，或上下文可能丢失时运行；不按命令、工具调用或普通对话轮次记录。
2. 区分事实与假设，保留仓库证据、测试结果和来源。
3. 已关联项目时，重新读取并追加当前任务唯一的设备独立 Session；没有时创建唯一文件。人工内容保留，不覆盖。
4. 未关联项目时，只创建 `project_id: null`、带时间戳和设备 ID 的 Inbox 草案；不得根据本地目录名建项目。
5. 决策、实验和经验候选默认先留在 Session。自动写入仅覆盖 Session 或 Inbox；修改 `status.md`、任一 index、正式内容、Daily、模板或文件位置必须确认。

## 结束工作（`shutdown`）

1. 在任务完成、暂停或交接前判断是否需要运行。只有存在持久结果、验证、决策候选、阻塞或明确下一步时才记录。
2. 只使用当前会话和仓库中的实际证据；来源不明的内容标为假设。
3. 已关联项目时复用当前任务 Session；没有映射时只写设备独立 Inbox。不得因收尾自动改写项目状态或索引。
4. 不把同一正文复制到 Daily、status、Lesson 和 Knowledge。Knowledge 候选只保留在来源记录，等待以后复核。
5. Vault 的 Git commit 和 push 只能在用户分别明确要求后执行；笔记写入不隐含 Git 授权。

## 每周整理（`weekly`）

1. 根据配置时区读取最近七天实际有活动的 Daily、Session、项目状态和必要索引；不扫描无关归档或附件。
2. 找出已完成工作、重复阻塞、过期事项、重复概念、Lesson/Knowledge 候选，并保留来源 Wikilink。
3. 按 [linking-and-health.md](linking-and-health.md) 检查元数据、重复 ID、裸链接、断链、索引覆盖、正式知识孤儿、模板权威和同步冲突迹象。
4. 创建或追加设备独立的 `00-Inbox/weekly-review-<year>-W<week>-<device-short>.md` 草案；保留人工内容并新增带时间戳章节。
5. 不自动修改项目状态、任何 index、Lesson、Knowledge、Decision、文件位置或 Git。没有新增候选、问题或待办时保持安静。

## 沉淀知识（`promote`）

1. 候选必须来自复核过的 Session、Inbox、Lesson、Decision、Experiment、Resource 或周整理草案。
2. 只搜索相关项目 Lesson、Area 和 Knowledge 主题范围；不得扫描整个 Vault。
3. 每个候选只提出一种处理：创建/保留项目 Lesson、创建 Knowledge、合并到已有 Knowledge、用新 Knowledge supersede 旧结论，或归档候选。
4. 展示来源、目标、类型、状态、去重理由、`derived_from`/`supersedes` 和完整差异。项目内容保留 `project_id`；Knowledge 必须归入明确 `topic_id`。
5. 用户确认后才创建或修改正式文件和共享索引。Knowledge 晋升后，来源通过反向链接可发现，不复制正文；被替代笔记标为 `deprecated`，不删除。

## 检查修复（`repair`）

1. 可以自动只读检查设备配置、必要目录、根和四个 collection index、项目映射、元数据、ID、链接、模板及同步异常。
2. 按 [linking-and-health.md](linking-and-health.md) 分类报告阻断项、需确认差异和提示；不自动删除孤儿或占位内容。
3. 检测到 Schema 1 时读取 [migration-v1-to-v2.md](migration-v1-to-v2.md)，进入 `repair` 的迁移子动作。必须先 dry-run、检查同步/写入者和冲突、准备外部 backup/staging，并展示完整迁移差异。
4. 普通修复按安全新增、元数据、链接/index、移动/删除分组确认；迁移则按已确认的完整批次应用，不能把部分成功声称为完成。
5. 修复后重新读取并运行同一检查。验证不可用、目标变化、出现新冲突或两次有证据的尝试失败时停止，不扩大范围。
