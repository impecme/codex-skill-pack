# 本机 Syncthing 引导（仅懒人包安装阶段）

本参考只由懒人包 05 安装流程读取。Codex 在对话中运行内置 Python 标准库辅助程序；不要求用户手动打开 Syncthing GUI、输入命令或运行一键安装器。日常项目工作、startup、checkpoint、shutdown 和普通 setup 不运行该程序。

## 授权范围

选择 05 或“全部”授权一次性执行以下本机增量操作：补齐 Schema 2 设备配置；在缺少 Syncthing 时安装锁定的官方版本；为本机已有 Vault 添加或复用一个暂停文件夹；限制监听为 loopback 并关闭发现、中继和 NAT；合并本机 .stignore；创建或复用当前用户的登录后台启动项。

该授权不包括添加远端设备、解除文件夹暂停、开放网络监听、开启发现/中继/NAT、防火墙修改、登录外部服务、Vault schema/笔记迁移、Git 操作或启动浏览器。

## 执行顺序

1. 在 Skill 源快照中读取 sources.lock.json 与本参考。通过 Codex 的 Python 3.8+ 环境调用 scripts/setup_syncthing.py preflight。预检为只读；不要使用真实配置目录做测试。
2. 预检优先复用 <CodexHome>/second-brain/config.json 中的 Vault 路径、设备 ID 和标签。设备配置文件不存在是正常首次安装情形，不视为整个懒人包失败；没有可用路径时只向用户一次性询问已存在的 Vault 目录，不创建空目录。输入路径必须存在且为目录。
3. 设备配置缺失时，路径确认后生成本机设备 ID、设备标签及 Schema 2 配置。预检识别 Syncthing 可执行文件、配置目录、正在运行的实例和用户级自启动项；运行进程查询失败不能当作“没有进程”。若有多个候选、无法读取的配置或启动项、Schema 1、不可解析配置、本机设备 ID 与 profile 证书不匹配、已有远端设备、目标 Vault 外的活动文件夹、目标 ID/路径冲突或不兼容程序，停止 Syncthing 相关写入；不要通过新建第二套配置绕过冲突。此类情况不阻断第二大脑 Skill、全局规则或其他所选 Skill 的安装。
4. 预检成功后，Codex 在对话中调用 scripts/setup_syncthing.py apply；若用户补充了 Vault 路径，将该值作为参数传入。程序仅使用锁定的官方发行包与 SHA-256，不升级现有 Syncthing。所有目标已有文件先备份到 <CodexHome>/second-brain/backups/<timestamp>-syncthing-setup/，再以临时文件原子写入。macOS/Linux 新建启动项使用同目录临时文件加原子“仅当目标不存在时创建”；若创建期间目标被其他程序占用，则停止且不覆盖。
5. Windows 注册/复用用户登录 Task Scheduler 任务；macOS 使用当前用户 LaunchAgent；Linux 优先使用 systemd 用户服务，否则使用 XDG 自启动。Windows 既有任务必须恰好包含一个可识别的 Syncthing `Exec` 动作、唯一启用的 `LogonTrigger`，以及当前用户的 `InteractiveToken`/最低权限 Principal（未写 `RunLevel` 时按 Windows 默认 `LeastPrivilege` 处理）；多动作、其他动作类型、非当前用户或无法核验的启动项均作为冲突停止，不覆盖或重复创建。新建启动项显式固定 GUI loopback、暂停状态、`--no-browser` 和 `--no-upgrade`（Windows 还需 `--no-console`）；复用项如提供这些参数则必须与基线一致。
6. 写入或启动前检查当前进程及平台登录服务管理器的 `STGUIADDRESS`、`STPAUSED`、`STUNPAUSED`、`STHOMEDIR`、`STCONFDIR`、`STDATADIR`；与本机 GUI 或暂停状态冲突、改变配置/数据目录、无法读取的环境变量，以及引用无法安全展开 `EnvironmentFile` 的 systemd 项，均视为冲突并停止相关写入。新建 LaunchAgent/systemd 项同时固定安全环境变量；正在运行的实例必须在命令行中明确固定 GUI 与暂停参数，因为无法追溯其启动时的环境。
7. 检查最终配置、忽略规则、自启动参数、后台进程以及 Syncthing 本机 API 的实际状态。API 只请求固定的 `127.0.0.1` 地址，禁用环境代理并拒绝 HTTP 重定向，避免把 API key 转发到其他地址。通过 `/rest/system/status`、`/rest/system/connections`、`/rest/config/devices` 和 `/rest/config/folders` 核实运行时本机设备 ID 与 profile 一致、设备列表只有本机、所有实时连接无远端、目标 Vault 文件夹路径一致且只关联本机并保持暂停；任何 API 不可用、结构异常或状态不符，都不能报告配置成功。Syncthing CLI 服务参数使用 `--no-browser`；Windows 后台运行还使用 `--no-console`。网页 GUI 仅绑定 loopback，不自动打开。

辅助程序只接受其所在仓库快照中的锁文件。不要从活动分支以外重新拼接辅助脚本或锁值；不能取得完整快照时，停止配置并报告。

## 配置基线与冲突

- Syncthing 配置目录先从已识别的启动项/运行进程参数中取得显式 --home；否则只接受唯一的现存标准配置目录。多个配置目录或配置目录残缺时停止。平台默认目录以 [Syncthing 命令行与配置目录说明](https://docs.syncthing.net/users/syncthing)为准。
- 现有配置必须能无歧义识别唯一本机设备且没有远端设备。任何文件夹引用远端设备，或目标 Vault 以外存在未暂停文件夹，均停止相关配置，不启动实例。目标 Vault 现有文件夹按实际路径复用其 ID；同路径多 ID、保留 ID 指向别处或路径规范化后冲突时停止。
- 本机 profile 使用 tcp://127.0.0.1:22000；Syncthing 2.x GUI 监听地址必须写入并验证 `<gui><address>127.0.0.1:8384</address></gui>` 子元素，不能用同名 XML 属性代替；重复地址字段视为冲突。关闭 globalAnnounceEnabled、localAnnounceEnabled、relaysEnabled、natEnabled 与 startBrowser；Vault 文件夹为 send/receive 类型但始终 paused=true。保留其他 XML 字段；运行中的实例如果需要离线配置修改则不改写，报告并停止。
- 为防配置正确但启动环境覆盖有效状态或改变 profile，服务命令行显式传入 `--gui-address=127.0.0.1:8384`、`--unpaused=false`、`--paused`；检测到会覆盖本机监听/暂停状态或改变 profile/data 目录的 Syncthing 环境变量时停止，不尝试改用户环境。已有正在运行进程缺少这些明确参数时，因无法核实其原始启动环境而停止。
- 对现有 profile 使用 Syncthing `device-id` 只读子命令，把证书派生的设备 ID 与唯一配置设备 ID 比较；证书缺失、命令不可用或不匹配均停止。预检记录第二大脑设备配置的内容指纹，apply 前变化时（尤其 Vault 路径变化）停止，不能沿用旧目标覆盖新配置。
- .stignore 只增补缺失的 /.git、/.claudian、/.obsidian/workspace*。既有自定义规则不排序、不删除、不改写；标记残缺、重复或文件不可读时停止。该文件本身不由 Syncthing 同步，每台设备都需本地配置。[Syncthing 忽略文件说明](https://docs.syncthing.net/users/ignoring.html)
- 新增本机文件夹不会创建或复制 Vault 内容。所有远端数量为零时报告“当前无远端连接”；实际跨设备连接和文件传输未验证。

## 安装结果报告

分别报告第二大脑 Skill、全局规则、本机设备配置、Syncthing 程序/profile、文件夹、忽略文件、自启动项和后台进程状态，并给出配置/备份位置。只有本机 API 验证通过才报告本机配置完成。至少包括 Vault 路径、Syncthing 版本及 profile 路径、folder ID 和暂停状态、loopback/network 开关、远端设备数、当前连接数、启动项类型、环境检查状态与是否打开浏览器。

若设置中途失败，保留备份和已完成阶段；不得自动删除原文件或回滚用户数据。准确列出已完成项与待处理项。没有远端设备时不得称为“同步成功”或“已验证多设备同步”。
