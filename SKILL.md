---
name: codex-lazy-pack
description: 个人 Codex 懒人包总入口：列出并按用户选择安装固定来源的工作流、工程、GitHub 和第二大脑相关 Skill。
---

# codex-lazy-pack

这是个人 Codex 懒人包的总入口。它只通过当前对话安装配置和 Skill，不执行本地一键安装脚本，也不作为 Codex 插件安装。

当用户把本仓库链接、仓库目录或本文件交给大模型，并要求安装个人懒人包时：

## 从仓库链接开始

先将本仓库作为安装说明读取，而不是直接把根目录交给普通 Skill 安装器。通过公开 HTTPS 获取一份仓库快照，
读取本文件、`sources.lock.json` 和 [共享安装规则](references/conversation-install.md)。同一次安装的全部入口、
references 和内置资产必须来自同一快照；具体下载方式、版本记录和新设备预检按共享规则执行。

用户已指定编号或“全部”时直接沿用选择，不重复询问。用户只给仓库链接时展示下方清单。

## 可用懒人包

| 编号 | 技能 | 内容 |
| --- | --- | --- |
| `00` | `codex-sol-luna-workflow` | 安装 Luna/Sol 工程工作流的用户级配置和 agent 配置 |
| `01` | `codex-mattpocock-engineering` | 安装 18 项工程技能，并配置对九项非自动调用 Skill 的全局建议规则 |
| `02` | `codex-github` | 安装 GitHub 连接与 GitHub CLI 工作流 Skill |
| `03` | `codex-obsidian` | 安装 Obsidian 连接与 Vault 访问工作流 Skill |
| `04` | `codex-github-obsidian` | 安装 GitHub + Obsidian 联动工作流 Skill |
| `05` | `codex-second-brain` | 安装第二大脑 Skill、合并全局规则，并配置本机暂停式 Syncthing |
| `全部` | — | 依次安装 `00` 至 `05` |

## 路由规则

1. 先读取 [`sources.lock.json`](sources.lock.json) 和共享安装规则，执行其中的新设备预检，再说明可用懒人包、固定 commit、目标路径和可能的配置影响。
2. 用户没有指定编号时，只列出上表并询问要安装哪些编号或“全部”；不要在用户选择前修改用户级文件。
3. 用户选择 `00` 时，读取并执行 [`skills/00-sol-luna-workflow/SKILL.md`](skills/00-sol-luna-workflow/SKILL.md)。
4. 用户选择 `01` 时，读取并执行 [`skills/01-mattpocock-engineering/SKILL.md`](skills/01-mattpocock-engineering/SKILL.md)，安装 18 项 Skill 并按确认流程合并 Matt Pocock 建议区块。
5. 用户选择 `02`、`03` 或 `04` 时，分别读取并执行对应子 Skill，安装参考仓库中的固定版本 Skill；用户选择 `05`
   时安装本仓库内置的 `codex-second-brain`、合并全局规则，并按该入口完成一次性本机 Syncthing 引导。该引导只写设备配置、
   Syncthing profile、Vault 根目录 `.stignore` 和用户级登录启动项；不读取/改写 Vault 笔记内容、不添加远端设备、不执行 Git 操作。
6. 用户选择“全部”时，依次读取并执行 `00` 至 `05`。来源安装冲突按对应子 Skill 处理；若仅 05 的 Syncthing 预检冲突，
   停止本机同步配置但保留其他已完成的 Skill 安装，并报告待处理项。
7. 外部来源必须按 `sources.lock.json` 中的固定 commit 获取；无法锁定时不得无提示改用 `main`/`master`。内置来源使用同一仓库快照和锁文件中的包版本，并报告可验证的快照身份。
8. 修改用户级文件前，必须读取现有内容、展示差异并备份；通过对话让用户选择合并、替换或跳过。受管
   `AGENTS.md` 区块使用稳定注释标记，重复安装只能原位更新，不能追加重复区块。`01` 的全局建议区块只写入基础 `AGENTS.md`，
   不改 `AGENTS.override.md`；安装 `00` 时保留已有的各懒人包受管区块。
9. 按共享规则分别报告文件安装、客户端发现和功能验证状态，以及来源版本、目标、备份和待处理项。仅复制完成不能声称技能已被加载或业务功能已验证；实际执行安装后，读取并在最终回复中提供[安装后验证提示词](references/post-install-verification-prompt.md)，
   供用户复制到新对话。

## 共同边界

- 不提供或要求用户自行运行一键安装脚本。仅 05 安装阶段允许 Codex 调用内置辅助脚本完成锁定范围内的本机 Syncthing 配置。
- 懒人包安装阶段不要求额外安装 Node.js、`npx`、`uv`、Git 或 GitHub CLI；05 使用已有 Python 3.8+ 标准库运行辅助脚本，不自动安装 Python。
- 懒人包安装阶段不执行 GitHub 登录、全局 Git 配置、仓库创建、push、Vault 笔记写入或项目文件修改；05 仅允许写设备配置和 Vault 根目录 `.stignore`。
- 安装 `05` 完成设备配置和本机 Syncthing 基线，但不初始化 Vault 内容、不配置远端设备，也不设置 GitHub 备份角色或每周任务。
  配置文件存在且 Vault 可访问后，全局自然维护规则才启用；普通项目工作不要求用户手动提醒启动、记录或收尾。
- 不自动安装 `sources.lock.json` 之外的 Skill、插件、MCP server 或凭证。
- 不把 token、密码或其他凭证写入仓库、`AGENTS.md`、Skill 文件或 Obsidian 笔记。
- 不把本仓库的入口文档复制成用户级 Skill；本仓库是对话式安装入口。

详细目标映射、固定来源和冲突处理规则见 [`references/conversation-install.md`](references/conversation-install.md)。
