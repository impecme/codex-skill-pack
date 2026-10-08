---
name: codex-mattpocock-engineering
description: 通过对话安装 mattpocock/skills Engineering 目录中固定 commit 的 18 项工程技能，并配置对九项非自动调用技能的全局建议规则。
---

# Matt Pocock Engineering 技能

仅在用户选择 `01` 或“全部”时执行本 Skill。

## 安装来源

先读取仓库根目录的 [`sources.lock.json`](../../sources.lock.json)，只使用 `mattpocock-engineering` 条目中的 repository、`sourceRoot` 和固定 commit。具体冲突规则见 [`references/conversation-install.md`](../../references/conversation-install.md)。

固定来源：

- 仓库：[mattpocock/skills](https://github.com/mattpocock/skills)
- 来源根目录：`skills/engineering`
- 目标：共享安装规则预检确定的用户级 `<SkillRoot>`。

## 必须安装的 18 项技能

`ask-matt`、`code-review`、`codebase-design`、`diagnosing-bugs`、`domain-modeling`、
`grill-with-docs`、`implement`、`improve-codebase-architecture`、`prototype`、`research`、
`resolving-merge-conflicts`、`setup-matt-pocock-skills`、`tdd`、`to-spec`、`to-tickets`、
`triage`、`wayfinder`、`wizard`。

## 执行要求

先执行共享安装规则的新设备预检，并读取 [Codex 兼容性说明](../../references/mattpocock-codex-compatibility.md)。
保留上游 Skill 文件及 `agents/openai.yaml` 的隐式调用限制，不修改其调用策略；静态校验告警、客户端发现、手动调用能力分别记录。

1. 按锁定 commit 获取上述 18 个目录的完整内容，不只复制每个目录的 `SKILL.md`，除非用户明确要求精简安装。
2. 逐个读取旧安装报告中的来源 commit 与文件清单；必要时从可信旧 commit 重建清单。已归本 Skill 管理的文件有差异时，先展示路径并备份整个 Skill 目录，核验后自动以锁定新版替换这些文件；旧来源已交付但新版删除的文件才可删除。用户修改过受管文件也以新版为准，并在报告注明。
3. 保留不在可信旧清单中的额外文件。新版新增文件与未知文件冲突、旧来源无法识别、目录中存在其他来源内容或跨扫描目录有同名 Skill 时，只暂停该 Skill 并一次性询问接管范围；不得清空目录或搬迁另一份 Skill。无旧安装记录时，先与可信历史锁定版本精确核对；仅凭 Skill 名称或目标路径不能证明所有权。
4. 如果当前 Skill 安装能力无法锁定指定 commit，按该 commit 下载对应目录；不得无提示改用 `main`/`master`。备份失败、目标自检查后发生变化或路径安全性无法验证时停止该 Skill 更新。
5. 把 `assets/global-skill-suggestion-section.md` 按共享规则合并至已记录的 `<CodexHome>/AGENTS.md` 目标中的
   `codex-lazy-pack-matt-skills-managed` 区块。有效且归属已确认的旧标记区块有差异时先备份整个文件，再自动原位更新；无标记但安装记录证明旧区块曾存在时备份并恢复新版。首次添加区块仍先展示差异并取得一次确认。先检查 override 是否遮蔽基础文件；默认不修改 override，只有旧安装记录包含用户对该 override 区块的明确确认时才原位更新。
   标记损坏或旧规则边界不明时只暂停建议区块，不影响 18 个 Skill 的独立更新。
6. 按共享规则逐项报告 18 个 Skill 的文件安装、客户端发现和功能验证状态，并单独报告建议区块状态、目标、归属依据、备份、override 遮蔽情况、
   commit、目录和缺失依赖；安装阶段不执行项目初始化。保留上游 `disable-model-invocation` 等调用限制，不因更新改变其行为。

全局建议规则只在具体项目工作与某项非自动调用 Skill 高度匹配时，建议最合适的一项并等待用户选择；不自动启动 Skill，
也不改变上游文件中的手动调用限制。匹配边界和拒绝后的行为以该全局区块为准。建议路由回归用例见
[`references/mattpocock-skill-suggestion-tests.md`](../../references/mattpocock-skill-suggestion-tests.md)。

本 Skill 不安装 Luna/Sol 工作流配置，也不安装插件、MCP server 或凭证；只有用户选择“全部”时，根入口才会先执行 `00`，再执行本 Skill。
