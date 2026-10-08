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
- 固定 commit：以 `sources.lock.json` 中的 `c1376779ada82ed540e052a74d23538c07f1a1e6` 为准
- 目标文件：`AGENTS.md`、`.codex/config.toml`、`.codex/agents/luna-worker.toml`、`.codex/agents/sol-advisor.toml`

## 执行要求

1. 执行共享安装规则的新设备预检，确定 `<CodexHome>`、有效全局规则，并分别检查 `gpt-6-luna` + `max` 与 `gpt-6.1-sol` + `high` 的本机可用性；无法确认的模型配置保持 `pending`，保留现有可运行设置。
2. 按锁定 commit 读取四个上游文件，不复制上游 README、文档或贡献指南。
3. 按以下映射安装到用户级 Codex 目录：

   | 上游路径 | 目标路径 |
   | --- | --- |
   | `AGENTS.md` | `<CodexHome>/AGENTS.md` |
   | `.codex/config.toml` | `<CodexHome>/config.toml` |
   | `.codex/agents/luna-worker.toml` | `<CodexHome>/agents/luna-worker.toml` |
   | `.codex/agents/sol-advisor.toml` | `<CodexHome>/agents/sol-advisor.toml` |

4. `sources.lock.json` 声明 `config.toml` 的受管键为 `model`、`model_reasoning_effort`、`agents.enabled`、`agents.default_subagent_model`、`agents.default_subagent_reasoning_effort` 和 `agents.max_concurrent_threads_per_session`。只有既有 00 安装记录或用户确认的接管范围能证明这些键已经归本 Skill 管理；已受管键有差异时先备份，再自动以锁定新版为准，未受管键、其他 table、注释和格式保留。新安装遇到现有冲突键而无归属证据时，只询问一次是否由本 Skill 接管这些键。
5. `luna-worker.toml` 和 `sol-advisor.toml` 仅在安装记录证明整文件归本 Skill 管理时自动替换；旧记录缺失时先与可信旧来源核对。用户配置、未知文件、符号链接/junction 或归属不明时停止该文件写入，不因目标文件名相同就覆盖。
6. `AGENTS.md` 工作流内容写入 `codex-sol-luna-workflow-managed` 标记区块；标记来自 `sources.lock.json`。合法区块有差异时备份整个文件并自动原位更新，保留其他 pack 区块及区块外正文。旧版无标记时，只有旧安装报告的 commit 能唯一证明完整文本边界、且移除其他有效区块后没有未归属正文，才自动转换；否则只询问一次边界/接管范围。其他受管标记残缺、重复或嵌套时停止对 `AGENTS.md` 的写入。
7. 所有自动更新前先在 `<CodexHome>/lazy-pack/backups/<timestamp>-<run-id>/` 备份目标并回读核验；写入前再次检查目标未变化。按共享规则分别报告每项的 `installed`、`already-current`、`updated`、`pending` 或 `failed`，并提供来源 commit、归属依据、路径、备份和待处理项。
8. 缺少模型、等级或客户端配置支持时，不安装未验证的模型覆盖，也不启用依赖它们的规则；保留现有可运行配置并报告相关单元 `pending`。模型可用性校验不得导致其他已确认受管且兼容的文件更新被跳过。

本 Skill 不安装 `mattpocock/skills` 的技能，也不安装插件、MCP server 或凭证；只有用户选择“全部”时，根入口才会继续路由到 `01`。
