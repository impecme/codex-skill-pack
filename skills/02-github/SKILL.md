---
name: codex-github-pack
description: 通过对话安装固定版本的 codex-github Skill，让 Codex 可以在之后主动配置 GitHub 工作流。
---

# GitHub Skill 安装包

仅在用户选择 02 或“全部”时执行本 Skill。

## 目标

本子 Skill 只安装参考懒人包中的 codex-github，不在本次安装中连接 GitHub 或修改 Git 配置。
用户之后可以通过“连接 GitHub”等对话主动触发已安装的 codex-github。

## 固定来源

先读取仓库根目录的 sources.lock.json，只使用 mathruffian-codex-lazy-packs 条目中的 repository、commit 和 sourcePath。

- 仓库：[mathruffian-dot/codex-lazy-packs](https://github.com/mathruffian-dot/codex-lazy-packs)
- 固定 commit：以 sources.lock.json 中的 574818e2d80b31807b74fcf62dd5b90b9e46ef3f 为准
- 源目录：skills/03-github
- 目标目录：<SkillRoot>/codex-github

先读取并执行[共享安装规则](../../references/conversation-install.md)的新设备预检，以其确定的 `<SkillRoot>` 为目标；完成后按共享规则分别报告文件安装、客户端发现和功能验证状态。

## 执行要求

1. 按固定 commit 获取源目录的完整内容，不只凭 main 或 master 的最新内容安装。
2. 读取旧安装报告和目标文件清单。内容相同则标记 `already-current`；有可信记录证明归本 Skill 管理的文件有差异时，展示路径、备份整个 Skill 目录并核验，然后自动更新为锁定版本。
3. 用户修改过受管文件也以新版为准；只删除旧清单中由本 Skill 交付且新版已移除的文件。未知附加文件保留；新版新增路径与未知文件冲突、旧来源无法识别或同名目录来源不明时，只暂停本 Skill 并一次性询问接管范围。
4. 无旧安装记录时，按可信旧 commit 重建来源清单并精确核对；不能仅凭同名或目标路径认定归属。来源无法锁定、备份失败、目标在检查后变化或路径安全性无法验证时停止该 Skill 更新，不静默覆盖。
5. 更新后重新读取目标 Skill，确认 frontmatter、目录结构和内容均可读，并记录新的文件清单、哈希、来源 commit 与备份位置。
6. 安装阶段只复制 Skill，不执行其中的 gh auth login、全局 Git 配置、创建仓库、commit、push 或连接器配置。

## 安全边界与报告

不要索要或保存 GitHub token、密码、SSH 私钥或其他凭证。安装完成后报告固定 commit、源目录、目标目录、状态、备份位置和是否需要重启 Codex。
如果用户想实际连接 GitHub，应在本 Skill 完成后让用户主动触发已安装的 codex-github，并对登录、全局配置和测试 push 分别取得确认。
