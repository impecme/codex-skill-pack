# 安装后验证提示词

安装或更新完成后，建议在**同一 Codex profile、目标项目目录下新开一条对话**，复制下面的提示词。新对话用于检查 Skill 发现和全局规则刷新；如果客户端仍未发现已安装的 Skill，再重启 Codex 后重试。

```text
请只读验收当前设备上的 codex-lazy-pack 安装。不要修改文件，不要安装依赖、登录或连接外部服务，不要执行 push、Vault 写入或其他外部副作用。

1. 确认当前工作区和可验证的 Codex profile、CODEX_HOME、用户级 Skill 扫描目录。无法从客户端或环境中确认的值请标为“未验证”，不要根据目录存在与否猜测。
2. 如果能访问本机安装报告，读取最近一份报告，列出本次选择的懒人包、锁定来源/版本、目标路径和各项状态。找不到报告时如实说明，不要推测。
3. 按本次选择核对目标文件是否安装完整。区分配置/agent 文件与真正的 Skill；仅发现 SKILL.md 文件不能证明 Codex 已加载该 Skill。
4. 使用当前客户端实际提供的 Skill 清单或发现诊断，报告相关 Skill 的名称和客户端显示的路径。若没有可用的客户端发现证据，将“Codex 发现”标为 unverified，不要用磁盘文件清单代替。
5. 检查全局指令的有效来源：确认 CODEX_HOME 下 AGENTS.override.md 是否优先于 AGENTS.md，并考虑当前项目中的 AGENTS 文件。只有文件优先级推断、没有运行时来源证据时，请明确标为“推断，未运行时确认”。
6. 若本次选择了 `01`，单独检查 `codex-lazy-pack-matt-skills-managed` 区块是否存在且只出现一份；报告基础 AGENTS.md 中的文件状态、当前客户端是否实际应用该规则、AGENTS.override.md 是否遮蔽它。不要把区块存在推断为规则已经生效。
7. 若本次选择了 `01`，使用有效全局规则对两个假设情境做只读判断，不调用 Skill、不修改项目：a) 用户给出已确认计划并要求实现，应该建议 `implement` 并等待选择；b) 用户只要求完成一个清楚的小改动，不应因此建议 `implement`。再逐项报告九项 Skill 的手动调用入口是否有客户端证据；不得仅凭文件已安装或规则会建议，就说手动调用可用。
8. 若存在已发现且适合当前项目、并且已确认可手动调用的其他 Skill，通过当前 Codex 支持的调用方式对本项目做一次无副作用的只读小测试；报告所用 Skill、调用方式和实际证据。没有合适 Skill、无法确认触发或缺少依赖时，标为 not-run 或 blocked，不要声称通过。不得为测试而实际执行可能写文件或操作外部服务的 Skill。
9. 进行任何第二大脑 Vault 功能检查前，先只读检查 `<CodexHome>/second-brain/sync-onboarding.json`。文件不存在，或其 `status` 为 `active` 且不含 `pendingOperation` 时，只有在 `<CodexHome>/second-brain/config.json` 有效且 Vault 可访问的前提下，才可只读验证 Vault 内容；状态文件不存在不代表配对、首次传输或双向同步已完成。若 `status` 缺失或不是 `active`，或存在任何 `pendingOperation`（包括 `status=active` 且存在 `pendingOperation`），不得读取或写入 Vault 内容；报告维护门禁和观察到的状态，只做安全的本机检查。GitHub/Obsidian 连接未配置时不要尝试登录或授权。整个验收不得启用设备发现/relay、开始传输、修改 Syncthing/网络/服务配置或更改 GitHub 配置。

请分别报告“文件安装”“客户端自动调用限制”“客户端手动调用能力”“全局建议规则/生效状态”“功能验证”及其证据，并列出待处理项。明确区分已证实事实、推断和未验证内容。
```
