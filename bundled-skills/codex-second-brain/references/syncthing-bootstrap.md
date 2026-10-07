# Syncthing 双机引导（仅懒人包安装阶段）

本参考只用于懒人包 `05` 安装流程。Codex 在两台设备各自的对话中调用包内的 [本机引导程序](../scripts/setup_syncthing.py) 和[配对辅助程序](../scripts/syncthing_pairing.py)；用户不需要手动打开 Syncthing GUI、输入命令或运行一键安装器。日常项目工作、`startup`、`checkpoint`、`shutdown` 和普通 `setup` 不运行这些程序，也不重配同步。

## 已确认的设备职责

- Windows 个人电脑保存主 Vault，也是唯一的 GitHub 人工备份设备。
- SSH Linux 服务器运行 Codex，使用服务器本地目录作为同一 Vault 的镜像；服务器不是 GitHub 备份设备。
- Syncthing 是两台设备之间唯一的实时内容同步通道。GitHub 私有仓库只由个人电脑人工备份，不承担实时同步。
- 每台设备的第二大脑 `config.json` 保存本机 Vault 路径和第二大脑 `deviceId`。Syncthing Device ID 是另一种标识；不得互换、推导或把其中一个当作另一个。
- Vault folder ID 固定为 `codex-second-brain-vault`。每台设备使用自己的本地路径；路径不放入配对卡，也不复制到另一台设备的配置中。
- 重复运行 `05` 时，若本机已经记录对端并进入配对、播种或晋级阶段，辅助程序只读核验已登记的双机身份、Vault 路径、folder 成员、阶段对应模式和网络安全基线；未暂停时返回 `existing-pair-no-changes`，当前 folder 或 peer 暂停时返回 `existing-pair-paused-no-changes`。`active` 阶段分别返回 `already-active-no-changes` 或 `active-sync-paused-no-changes`。它不会套用首次安装的“本机-only、全暂停”配置、改变同步状态或自动修复配置漂移；不匹配时停止并报告。静态 profile 核验不代表实时连接或跨设备内容已验证。

## 人工介入点与配对卡

用户通过两台设备各自的 Codex 对话手动交换配对卡。辅助程序生成的卡片含 Syncthing Device ID、设备标签、固定 folder ID、设备角色、初始传输方向和当前 folder 类型/暂停状态。手动交换时还要附上本节规定的连接策略：loopback TCP 加官方 dynamic relay、global discovery/public relay 开启、LAN discovery/announce 关闭、Syncthing NAT mapping 关闭、浏览器自动打开关闭。卡片不得包含本地路径、凭证、SSH 私钥或第二大脑 `config.json` 的 `deviceId`。

公共设备发现/relay 会处理设备 ID、IP 等连接元数据；文件内容的设备间传输使用 TLS 加密。接受此连接策略后再交换卡片。服务器若无法访问发现或 relay 服务，Codex 只报告受阻状态，由你或管理员决定网络变更。

人工介入点：

1. 在各自的 Codex 对话中确认设备角色和本地路径。个人电脑路径必须指向已存在的主 Vault。服务器目标路径由用户确认；可使用已存在的空目录，或在确认目标后创建空目录。接收端空目录检查只豁免 `.stignore`、`.stfolder`；出现其他内容即停止，不覆盖或合并。
2. 用户在两边的 Codex 对话中核对并手动交换配对卡。
3. 服务器报告 `receiver-ready` 后，用户确认两边的 Obsidian、Codex 和其他 Vault 写入者均已停写；Codex 才启动首次传输。
4. 服务器接收核验通过后，用户确认把服务器 folder 从 `receiveonly` 升为 `sendreceive`。
5. 服务器状态和两端 manifest 再次核验通过后，用户确认把个人电脑 folder 从 `sendonly` 升为 `sendreceive`。是否执行双向写入探针需另行取得用户授权。
6. 两端各自 `complete` 前，用户需在对应 Codex 会话提供另一端最近的 manifest SHA-256 和双向配置/连接核验结果；两端都通过后才恢复该设备的自然维护。
7. 若设备不能经发现或公共中继连通，用户自行决定是否手动调整网络。不得自动更改路由器或防火墙。

## 双机状态机

只按本参考的语义步骤调用辅助程序；不要猜测或编造未实现的参数或行为。遇到未知设备、身份或路径冲突、非空服务器目标、状态无法核验、冲突文件或其他 Vault 写入者未停写时，停止相关写入与传输并报告。

1. **本机准备。** 在个人电脑核实主 Vault、第二大脑配置和本机 Syncthing 身份；在服务器核实用户确认的本地目标路径及其内容为空。两边分别配置本机设备，不复制 Vault 路径或设备配置文件。`.git` 留在个人电脑并由本机 `.stignore` 排除。此阶段只保留 TCP loopback，发现和中继关闭；Vault 文件夹保持暂停，不传输内容。
2. **配对并保持暂停。** 用户核对并交换配对卡及连接策略。说明公共设备发现/官方 relay 会处理 Device ID、IP 等连接元数据并取得明确确认后，Codex 才调用 `pair --confirmed-network-metadata`。配对辅助程序将唯一核验过的远端加入设备表和 Vault 文件夹成员；PC 端 folder 类型为 `sendonly`，服务器端为 `receiveonly`，两端 folder 和远端设备仍暂停，因此此步不会开始传输。配对完成不等于用户已授权首次传输。配对后的监听地址为 `tcp://127.0.0.1:22000` 和 `dynamic+https://relays.syncthing.net/endpoint`；启用 global discovery/public relay，关闭 LAN discovery/announce、Syncthing NAT mapping 和浏览器自动打开。
3. **准备接收端。** 服务器确认目标路径、内容为空并取得用户对解除接收端暂停的本阶段明确确认后，才调用 `arm-receiver --confirmed-arm-receiver`。辅助程序核实唯一配对设备后，解除服务器接收 folder 与服务器端远端设备的暂停，回读两者状态并报告 `receiver-ready`。PC 源 folder 和 PC 端远端设备仍暂停，所以此时仍不传输。
4. **首次单向传输。** 只有用户确认双方写入者已停写，且 Codex 已核实服务器为 `receiver-ready`，才执行 `start-source`。PC 源端解除暂停并以 `sendonly` 向服务器 `receiveonly` 传输。两边的 Obsidian、Codex 和其他 Vault 写入者继续停写，直到接收和内容核验通过。辅助程序执行成功本身不代表用户确认，也不代表传输完成。
5. **核验服务器接收。** 先在 PC 停写期间生成 manifest SHA-256，再在服务器运行 `verify-seed` 并提供该 64 位指纹。指纹参数为必填门槛；缺少或不相等时辅助程序拒绝返回 `seed-verified`，不得晋级。服务器 folder 必须为未暂停的 `receiveonly`、恰有一个已连接远端、Syncthing folder 状态为 `idle`，`needTotalItems`、`needBytes`、`needDeletes`、`pullErrors` 和 `receiveOnlyTotalItems` 均为零。manifest 只输出整体 SHA-256、文件/目录数和总字节，不输出路径名；它纳入相对路径、类型、大小和文件内容哈希，并排除 `.git`、`.claudian`、`.stignore`、`.stfolder`、`.obsidian/workspace*`。自定义忽略规则可能导致指纹不同；不匹配时保留单向模式，检查原因，不绕过门槛。
6. **先晋级服务器。** 核验服务器接收后，用户再次确认双方应用写入者停写、PC 最新报告仍处于预期 `sendonly` 播种阶段并批准本阶段；Codex 才执行 `promote-server`（传入 `--confirmed-verified --confirmed-writers-paused --confirmed-peer-state` 和 PC 源 manifest SHA-256），把服务器从 `receiveonly` 改为 `sendreceive`。此时 PC 仍为 `sendonly`，所以尚未进入双向配置。继续停写，并核验服务器 status 及 manifest。
7. **再晋级个人电脑。** 服务器 status 和 manifest 再次核验通过、唯一连接及同步状态符合要求后，用户确认服务器已晋级、双方应用写入者停写并批准本阶段；Codex 才执行 `promote-primary`（传入相同的三个确认标记和服务器 manifest SHA-256），把 PC 从 `sendonly` 改为 `sendreceive`。只有两端均为 `sendreceive` 后才进入双向配置状态；双向写入是否实际可用，仍须在用户另行授权探针后验证。
8. **恢复日常维护。** 两边分别执行 `complete`，传入对端最近的 manifest SHA-256，并确认双方 status、连接、模式和内容一致。辅助程序再次核验本机 idle/无待同步项/错误并把本机 `<CodexHome>/second-brain/sync-onboarding.json` 标为 `active`。全局规则只有在本地 `status=active` 且没有 `pendingOperation` 时才恢复自动读取/写入 Vault；中断设备需在恢复后单独完成该核验。缺少对端最新证据时不得标记完成。状态文件不是跨设备同步成功的替代证据。

## 网络、启动与本机安全

- 配对后的 Syncthing 监听地址为 `tcp://127.0.0.1:22000` 与官方 `dynamic+https://relays.syncthing.net/endpoint`；启用 global discovery 和 public relay，关闭 LAN discovery、LAN address announce、浏览器自动打开及 Syncthing 的 UPnP/NAT mapping。`natEnabled=false` 只禁用 Syncthing 的自动 NAT/UPnP 映射，不修改路由器或防火墙。不能连通时报告现状，等待用户决定是否手动调整网络。
- 修改发现/监听配置后先读取 `/rest/config/restart-required`；若要求重启，仅通过已验证的本机 REST API `/rest/system/restart` 重启当前 profile，等待 API 恢复后重新核验进程 profile、Device ID 和 restart-required=false。不得打开浏览器、手动改写运行中的 `config.xml` 或因超时声称配置已生效；超时保留备份并报告部分进度。
- Syncthing GUI 只监听 `127.0.0.1`，API 只访问固定 loopback 地址；禁用环境代理并拒绝 HTTP 重定向。按阶段核实 `/rest/system/status`、`/rest/system/connections`、`/rest/config/devices` 和 `/rest/config/folders` 的实际状态。API 不可用、结构异常或结果不符时，不得报告该阶段完成。
- 启动项不得带 `--paused`，也不得设置 `STPAUSED` 或 `STUNPAUSED`。使用 Syncthing 配置中持久化的 folder `paused` 状态控制各阶段；重启后按保存状态恢复。环境中存在非空 `STPAUSED`/`STUNPAUSED` 时停止并报告，不自动清理。启动只固定 GUI loopback，并使用 `--no-browser`、`--no-upgrade`；Windows 还使用 `--no-console`。
- Windows 使用当前用户、交互式、最低权限的 Task Scheduler 登录任务；复用项必须恰有一个可识别的 Syncthing 动作、唯一启用的登录触发器及当前用户的 `InteractiveToken`/最低权限 Principal。macOS 使用当前用户 LaunchAgent。桌面 Linux 优先使用 systemd 用户服务，否则才使用 XDG 自启动。
- SSH 或无桌面的 Linux 必须使用 `systemd --user`，并核实 systemd user manager 可用且 linger 已启用；不得退回或复用 XDG 自启动。无桌面环境下发现既有 XDG 项时也作为冲突停止。linger 缺失或无法确认时停止，不提权代办；引导用户自行在服务器运行 `sudo loginctl enable-linger <用户名>`，完成后重新执行 05。无桌面环境下若 systemd user manager 不可用，停止，不使用 XDG 自启动，也不以 root 运行 Syncthing。
- 继续只读检查当前进程和平台登录服务管理器中的 `STGUIADDRESS`、`STHOMEDIR`、`STCONFDIR`、`STDATADIR`。路径或 GUI 冲突、环境不可读、profile 歧义、Syncthing Device ID 与证书派生身份不符、程序/启动项不可核验或目标变化时停止相关写入。不得通过创建第二套 profile 绕过冲突。
- `setup_syncthing.py` 只使用当前懒人包快照的锁文件；缺少 Syncthing 时才安装锁定官方版本并校验 SHA-256，不升级已有版本。预检只读，不能用真实配置目录做 apply 测试。写入前备份目标已有文件，使用安全的临时文件/原子写入；目标被其他程序占用或运行中 profile 需要离线修改时停止且不覆盖。`.stignore` 每台设备分别维护，只补齐缺失的 `/.git`、`/.claudian`、`/.obsidian/workspace*`；保留其他规则，具体格式见 [Syncthing 忽略文件说明](https://docs.syncthing.net/users/ignoring.html)。
- 不创建周期自动化，不自动执行任何 Git 操作。GitHub 私有仓库仅由 PC 在用户明确要求并逐项确认时人工 `add`、`commit`、`push`；服务器不初始化或维护该 Vault 的 `.git`。详见[GitHub 私有仓库人工备份引导](github-backup-bootstrap.md)。

## 分阶段报告

每阶段只报告实际核验结果；未知值明确标为未知或待验证。设备路径只在对应设备的本地 Codex 对话中报告，不写进配对卡。

| 阶段 | 必须报告 |
| --- | --- |
| 本机准备 | 设备角色；本机 Syncthing 身份与第二大脑 `deviceId` 的分别核验结果；本机路径核验、服务器目标空目录检查；profile、版本、启动项、folder 暂停状态和冲突检查。 |
| 配对暂停 | 两张卡中的设备标签、Syncthing Device ID、folder ID、角色/连接策略；设备表与 folder 成员；PC `sendonly`、服务器 `receiveonly`；两端 folder/设备仍暂停；loopback/relay/discovery/NAT/浏览器设置和实际连接/relay 可达状态。 |
| 接收准备 | 服务器 `receiver-ready`、folder 类型与暂停状态、唯一远端、空目录检查；PC 源 folder/对端仍暂停；尚未开始传输。 |
| 首次传输 | 用户确认两边写入者停写；服务器 `receiver-ready` 已核验；PC `sendonly` 到服务器 `receiveonly` 的实际传输状态及冲突检查。 |
| 接收核验 | 服务器唯一连接、`idle`、各项 needs/errors 为零；PC 与服务器 manifest 必须比较且 SHA-256 相等；未决冲突。 |
| 服务器晋级 | 用户确认、服务器已 `sendreceive`、PC 仍 `sendonly`；服务器当前 status/manifest 和停写状态。不得报告双向同步已启用。 |
| PC 晋级与双向核验 | 用户确认、两端均为 `sendreceive`、连接/状态/manifest 检查；双向写入探针是否另获授权及实际结果。未验证时标为待验证。 |
| 完成引导 | 两端各自 `complete` 的核验结果与 onboarding 阶段；只有本机与对端证据均对上后才标记本地 `active`、恢复自然维护。 |

配置项已写入不等于设备发现或公共中继实际可达。没有连接验证前，不得声称设备已连通、公共中继可达、首次传输完成、服务器已 up-to-date 或双向同步已验证；本机配置或配对成功不等于多设备同步完成。

## 中断恢复与安全边界

- `arm-receiver`、`start-source`、`promote-server` 和 `promote-primary` 在首次修改同步有效状态前，先把 `pendingOperation` 原子写入本机 `<CodexHome>/second-brain/sync-onboarding.json`；记录本机/对端 Syncthing Device ID、Vault 路径、folder ID、源/目标模式、原阶段、备份位置、操作 ID、所需确认；晋级操作还记录此前核验的双端 manifest SHA-256。只有 API 回读验证 folder、对端、活动状态和内容基线后，才以单次原子状态写入推进 `status` 并清除 `pendingOperation`。
- 所有会改变本机同步阶段的辅助操作使用同一把位于 Syncthing profile 下的本机锁串行执行。`status=active` 但仍有 `pendingOperation` 也视为 HOLD：全局规则必须暂停 Vault 自动恢复与写入。
- 四种阶段操作的 API 修改、扫描、最终状态核验或本地状态提交失败时，辅助程序保留原错误，然后尽力按“先暂停确切 Vault folder，再暂停记录的确切对端设备”执行补偿，随后分别重新读取两者的 `paused` 状态。错误报告逐项展示实际观测、失败/未知原因；只有两者身份均核验且都回读为 `true` 才报告 `containmentVerified=true` / `syncthingChangesStopped=true`。任何一项未知或未暂停都不得声称同步已停止。
- `setup_syncthing.py` 的预检、配置或服务设置失败，只能证明安装器停止了自己的后续写入；它没有执行传输隔离，因此报告 `syncthingChangesStopped=null`、`containmentVerified=false`。不得据此推断 Syncthing 当前没有传输。配对阶段辅助程序失败时则依据实际 containment 回读分别报告 `true` 或 `false`。
- 若阶段完成文件已原子替换可见、但父目录 `fsync` 返回错误，程序先尽力隔离同步，再用相同 `operationId`、身份与内容基线恢复一个明确标注 `completionCommitUncertain` 的 HOLD；阶段保持已观察到的完成值，不回退。后续必须在新的调用中重新确认，并重新核验路径、身份、文件内容及该阶段条件，才可按同一 operation 恢复。恢复 HOLD 的状态文件写入若也失败，会逐项报告状态写入错误；不得声称持久化恢复记录已建立或自动解除暂停。
- 若 Codex/辅助进程在 pending 写入后被强制终止，下一次任何会变更同步的操作先尝试暂停并核验两项目标，然后仅记录 HOLD 并结束本次调用；不能在一次调用中边恢复边重新启动。用户需在新的调用中重新确认对应条件，辅助程序再次核验目标仍全部暂停、路径/身份/文件内容满足前提后，才可重试。旧 pending 中保存的确认仅供审计，不能代替新的用户确认。
- 晋级恢复只接受 pending 中记录的源模式或 `sendreceive` 目标模式：源模式表示待执行的晋级仍需应用；目标模式表示类型修改已生效但状态/核验提交中断，可在稳定内容指纹复核后跳过重复 PATCH。其他模式、身份/成员变化或本地内容偏离基线都进入 HOLD。恢复时先在暂停状态核对基线与用户重新提供的对端 SHA-256，再在 pending 仍有效时恢复本机连接，重新验证唯一连接、idle、needs/errors 和指纹，之后才可提交晋级阶段；不会回滚类型或清除文件。
- 重试必须沿用原操作及相同本机、对端、Vault 路径和 folder 身份；未知身份时不触碰未知设备，只暂停能够由固定 folder ID + 本机路径 + 精确成员关系确认的 folder。服务器接收目录若已有任何部分内容，`arm-receiver` 不会清理、覆盖或合并；先保留文件并报告冲突。
- 该机制是尽力隔离，不是对操作系统级强制终止的绝对保证：若 Codex 被杀、Syncthing API 不可用或设备掉线，活动传输可能持续到 Syncthing 自身暂停或下一次 Codex 恢复操作。报告必须明确 containment 是否实际核实，不得承诺网络中断时已即时停止。
