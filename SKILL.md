# codex-lazy-pack

这是一个个人 Codex 懒人包的对话式安装入口。

当用户把本仓库链接、仓库目录或本文件交给大模型，并要求安装个人懒人包时：

1. 读取 `sources.lock.json`，向用户说明将安装的两个来源、固定 commit、目标路径和可能的配置影响。
2. 第一套来源全部安装：将其可生效的 `AGENTS.md`、`.codex/config.toml` 和两个 agent 配置写入用户级 Codex 目录。
3. 第二套来源全部安装：安装 `mattpocock/skills` 的 Engineering 目录中的 18 项技能。
4. 优先使用当前环境可用的 Codex Skill 安装能力；如果安装器无法锁定指定 commit，则按锁定 commit 下载对应目录，不要无提示改用 `main`/`master` 最新内容。
5. 修改用户级文件前检查现有内容。发现冲突时显示差异，先备份，再通过对话让用户选择合并、替换或跳过；不得静默覆盖。
6. 安装完成后报告每个来源和技能的结果、目标路径、备份位置以及未完成的手动操作。

本入口不执行 PowerShell、Shell 或其他一键安装脚本，也不自动安装未列入 `sources.lock.json` 的插件、MCP server、凭证或额外 Skill。

详细的目标映射、固定 commit 链接和冲突处理规则见：
`references/conversation-install.md`。
