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
| `01` | `codex-mattpocock-engineering` | 安装 `mattpocock/skills` Engineering 目录中的 18 项技能 |
| `02` | `codex-github` | 安装 GitHub 连接与 GitHub CLI 工作流 Skill |
| `03` | `codex-obsidian` | 安装 Obsidian 连接与 Vault 访问工作流 Skill |
| `04` | `codex-github-obsidian` | 安装 GitHub + Obsidian 联动工作流 Skill |
| `05` | `codex-second-brain` | 安装第二大脑 Skill，并把自然维护规则合并到用户级 `AGENTS.md` |
| `全部` | — | 依次安装 `00` 至 `05` |

## 路由规则

1. 先读取 [`sources.lock.json`](sources.lock.json) 和共享安装规则，执行其中的新设备预检，再说明可用懒人包、固定 commit、目标路径和可能的配置影响。
2. 用户没有指定编号时，只列出上表并询问要安装哪些编号或“全部”；不要在用户选择前修改用户级文件。
3. 用户选择 `00` 时，读取并执行 [`skills/00-sol-luna-workflow/SKILL.md`](skills/00-sol-luna-workflow/SKILL.md)。
4. 用户选择 `01` 时，读取并执行 [`skills/01-mattpocock-engineering/SKILL.md`](skills/01-mattpocock-engineering/SKILL.md)。
5. 用户选择 `02`、`03` 或 `04` 时，分别读取并执行对应子 Skill，安装参考仓库中的固定版本 Skill；用户选择 `05`
   时安装本仓库内置的 `codex-second-brain`，并将其受管自然维护区块合并到 `<CodexHome>/AGENTS.md`。安装阶段均
   不执行登录、推送、Vault 写入或定时任务创建。
6. 用户选择“全部”时，依次读取并执行 `00` 至 `05`；任何一个来源出现冲突或失败，都要先报告并遵循冲突规则，不要静默继续覆盖。
7. 外部来源必须按 `sources.lock.json` 中的固定 commit 获取；无法锁定时不得无提示改用 `main`/`master`。内置来源使用同一仓库快照和锁文件中的包版本，并报告可验证的快照身份。
8. 修改用户级文件前，必须读取现有内容、展示差异并备份；通过对话让用户选择合并、替换或跳过。受管
   `AGENTS.md` 区块使用稳定注释标记，重复安装只能原位更新，不能追加重复区块。
9. 按共享规则分别报告文件安装、客户端发现和功能验证状态，以及来源版本、目标、备份和待处理项。仅复制完成不能声称技能已被加载或业务功能已验证；实际执行安装后，读取并在最终回复中提供[安装后验证提示词](references/post-install-verification-prompt.md)，
   供用户复制到新对话。

## 共同边界

- 不执行 PowerShell、Shell 或其他一键安装脚本。
- 懒人包安装阶段不要求额外安装 Node.js、`npx`、`uv`、Git 或 GitHub CLI；这些工具可能由之后主动使用的 GitHub/Obsidian Skill 检查或引导配置。
- 懒人包安装阶段不执行 GitHub 登录、全局 Git 配置、仓库创建、push、Vault 写入或项目文件修改。
- 安装 `05` 不等于初始化第二大脑；建库、设备配置、Syncthing/GitHub 角色确认和每周任务仍需之后显式开始。设备配置尚不存在时，
  全局自然维护规则保持休眠；完成一次性配置后，普通项目工作不再要求用户手动提醒启动、记录或收尾。
- 不自动安装 `sources.lock.json` 之外的 Skill、插件、MCP server 或凭证。
- 不把 token、密码或其他凭证写入仓库、`AGENTS.md`、Skill 文件或 Obsidian 笔记。
- 不把本仓库的入口文档复制成用户级 Skill；本仓库是对话式安装入口。

详细目标映射、固定来源和冲突处理规则见 [`references/conversation-install.md`](references/conversation-install.md)。
