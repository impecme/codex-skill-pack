# codex-lazy-pack

这是我的个人 Codex 懒人包。它把常用工程工作流和代码工程技能固定到指定 commit，新机器
上只需要把这个仓库交给大模型，通过对话即可完成用户级配置。

本项目同时包含：

- 对话式安装入口：`SKILL.md`
- 上游版本锁定清单：`sources.lock.json`
- 详细安装规则：`references/conversation-install.md`

## 快速开始：通过对话安装

将本仓库链接或目录交给 Codex，并发送类似请求：

```text
请读取这个 codex-lazy-pack，按照 sources.lock.json 安装全部个人常用配置和技能。
安装前先检查已有配置，冲突时展示差异并询问我，不要静默覆盖。
```

大模型应先读取 [SKILL.md](SKILL.md) 和
[对话式安装规则](references/conversation-install.md)，再检查环境和
已有配置，最后逐项安装并报告结果。

## 安装内容

### Luna/Sol 工程工作流

来源：[sol-luna-engineering-workflow](https://github.com/BruceLanLan/sol-luna-engineering-workflow)

锁定 commit：`ed13d90a055630aa89427b20b8a0a2401dc8a47b`

安装到用户级 Codex 目录（通常是 `~/.codex`）：

- `AGENTS.md`
- `config.toml`
- `agents/luna-worker.toml`
- `agents/sol-advisor.toml`

上游 README、文档和贡献指南不会被复制到用户配置目录。

### Engineering 技能

来源：[mattpocock/skills Engineering](https://github.com/mattpocock/skills/tree/main/skills/engineering)

锁定 commit：`3cca18b368ae95cdbdebbff572ccafa662551015`

全部 18 项都会安装到用户级 Skill 目录：

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

## 对话式安装行为

- 大模型直接使用可用的 Codex Skill、文件和仓库工具完成安装。
- 上游内容按 `sources.lock.json` 中的 commit 获取，不跟随 `main`/`master` 漂移。
- 不执行本地一键安装脚本，不要求额外安装 Node.js、`npx`、`uv`、Git 或 GitHub CLI。
- 不要求 GitHub 登录，不自动配置凭证。
- 配置或同名 Skill 冲突时，先展示差异并询问用户。
- 安装完成后提示是否需要重启 Codex，以便刷新新 Skill。

## 冲突、备份和恢复

已有文件不会被静默覆盖。发生冲突时，大模型应：

1. 显示当前文件与上游文件的差异。
2. 对替换或手动合并的内容先备份到 `<CodexHome>/lazy-pack/backups/<时间戳>`。
3. 通过对话让用户选择替换、跳过或手动合并。
4. 未完成的手动合并保留为 pending，并在最终报告中说明。

重复安装时，同一 commit 且内容相同的技能会直接跳过；不同来源或已被修改的同名技能会
再次进入冲突流程。

## 个人开发中的推荐用法

安装后，可以把这些技能组合成通用开发闭环：

1. 用 `grill-with-docs` / `to-spec` 固化目标、约束和验收标准。
2. 用 `prototype` 验证不确定的设计或建立 baseline。
3. 用 `implement` / `tdd` 开发，并保持测试和检查可重复执行。
4. 用 `diagnosing-bugs` 根据证据排查错误和回归。
5. 用 `code-review` / `codebase-design` 检查实现质量和架构边界。
6. 用 `research` 查询需要的一手资料。

## 更新锁定版本

懒人包不会自动追踪上游最新版本。需要升级时，维护者应先修改 `sources.lock.json` 中的
commit，检查上游变更，再提交这个懒人包的版本更新。这样不同机器仍能复现同一套环境。

## 插件/MCP扩展

`sources.lock.json` 已预留 `extensions.plugins` 和 `extensions.mcp` 数组。本版不会自动扫描
或安装未确认的插件、MCP server 或凭证配置。本项目本身不作为 Codex 插件安装。

## 范围说明

当前版本只封装上面两个 GitHub 来源。工作区中的本地资料不会自动复制；如需加入个人常用
资料或 Skill，可以在后续版本追加为第三组来源。
