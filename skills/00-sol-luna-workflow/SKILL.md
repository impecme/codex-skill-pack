---
name: codex-sol-luna-workflow
description: 通过对话安装固定 commit 的 Luna/Sol Codex 工程工作流配置、AGENTS.md 和两个 agent 配置。
---

# Luna/Sol 工程工作流

仅在用户选择 `00` 或“全部”时执行本 Skill。

## 安装来源

先读取仓库根目录的 [`sources.lock.json`](../../sources.lock.json)，只使用 `sol-luna-engineering-workflow` 条目中的 repository 和固定 commit。具体冲突规则见 [`references/conversation-install.md`](../../references/conversation-install.md)。

固定来源：

- 仓库：[impecme/sol-luna-engineering-workflow](https://github.com/impecme/sol-luna-engineering-workflow)
- 上游仓库：[BruceLanLan/sol-luna-engineering-workflow](https://github.com/BruceLanLan/sol-luna-engineering-workflow)
- 固定 commit：以 `sources.lock.json` 中的 `ada4058bfa2f6a7c718c72d7c2b9c555eb3eea38` 为准
- 目标文件：`AGENTS.md`、`.codex/config.toml`、`.codex/agents/luna-worker.toml`、`.codex/agents/sol-advisor.toml`

## 执行要求

1. 确认当前 Codex 用户目录，通常是 `~/.codex`；Windows 通常是 `%USERPROFILE%\.codex`。
2. 按锁定 commit 读取四个上游文件，不复制上游 README、文档或贡献指南。
3. 按以下映射安装到用户级 Codex 目录：

   | 上游路径 | 目标路径 |
   | --- | --- |
   | `AGENTS.md` | `<CodexHome>/AGENTS.md` |
   | `.codex/config.toml` | `<CodexHome>/config.toml` |
   | `.codex/agents/luna-worker.toml` | `<CodexHome>/agents/luna-worker.toml` |
   | `.codex/agents/sol-advisor.toml` | `<CodexHome>/agents/sol-advisor.toml` |

4. 每个目标文件都先与现有文件比较。相同则标记 `already-current`；不同则展示差异、备份现有文件，再让用户选择手动合并、使用上游版本或保留现有版本。
   更新 `AGENTS.md` 时，识别并保留由其他懒人包以成对注释标记的受管区块；尤其不得因应用工作流上游版本而删除
   `codex-second-brain-managed` 区块。发现残缺或重复标记时停止自动合并并报告冲突。
5. 无法安全判断 TOML 语义时，不猜测合并结果；保留双方文件并将该项标记为 `pending`。
6. 安装完成后逐项报告四个文件的状态、使用的 commit、目标路径、备份路径和未完成操作。

本 Skill 不安装 `mattpocock/skills` 的技能，也不安装插件、MCP server 或凭证；只有用户选择“全部”时，根入口才会继续路由到 `01`。
