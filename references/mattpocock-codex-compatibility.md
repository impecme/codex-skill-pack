# Matt Pocock Engineering 的 Codex 兼容性

执行 `01` 的安装、更新和验收时读取。来源仍是锁文件中的 18 项 Engineering Skill；本文件不增加安装来源。

## 已确认的事实

锁定 commit `3cca18b368ae95cdbdebbff572ccafa662551015` 的 18 个目录可以公开下载。以下 9 项包含
`disable-model-invocation: true`，当前本机 `quick_validate.py` 报告该字段不在允许列表中：

`ask-matt`、`grill-with-docs`、`implement`、`improve-codebase-architecture`、`setup-matt-pocock-skills`、
`to-spec`、`to-tickets`、`triage`、`wayfinder`。

这些目录同时提供 `agents/openai.yaml` 的 `policy.allow_implicit_invocation: false`，表示不允许模型隐式调用；复制时必须保留该文件。
这与用户显式手动调用是不同状态，不能据此推断当前客户端的手动菜单一定可见或可用。校验器的字段告警不能单独证明客户端拒绝加载，
也不能证明客户端支持该额外字段；实际发现和手动调用能力应分别由当前客户端验证。参见
[Codex Skill 元数据与调用策略](https://developers.openai.com/codex/skills)。

`grill-with-docs` 等 Skill 引用了 `grilling`，但该 Skill 不在当前已确认的 18 项 Engineering 清单中。
全新设备不能假设已存在它。`wizard` 的后续使用依赖 Bash；Windows 安装文件成功不代表本机能运行它生成的向导。

## 安装与使用检查

1. 完整复制锁定目录，保持上游内容和调用策略；不为了让静态校验器通过就删除 frontmatter 字段或改写正文。
2. 静态检查要求 name、description、YAML 和引用资源可读。记录未知字段告警，再检查客户端是否发现该 Skill。
   未取得发现证据时标记 `unverified`，不能把告警升级成“加载失败”或忽略后宣称“已可用”。
3. 检查被调用技能是否可用，特别是 `grilling`。已确认缺少依赖时，文件仍可标记 `installed`，相关功能标记
   `blocked` 并列出依赖；保留其他独立功能。不自动安装确认清单之外的技能，用户选择补装后另行确定来源和版本。
4. 正文中的 `/skill-name` 和 “Call the Skill tool” 属于跨客户端调用表达。实际使用时通过当前 Codex 支持的
   Skill 调用方式或读取对应已安装 `SKILL.md` 执行；不能假装存在一个未提供的工具。显式调用入口参考 `$skill-name`。
   若手动菜单或显式调用能力未在当前客户端实际验证，报告 `unverified`，不要由安装状态推导为可用。
5. `setup-matt-pocock-skills` 配置的是每个项目的 tracker/labels/docs；安装到用户级目录后，不自动对所有项目运行它。
   `wizard` 的 Bash、GitHub 凭证、项目配置等运行依赖在主动使用时检查，不在懒人包安装阶段补装。
6. 只有当前客户端实际拒绝加载、忽略策略或无法执行必要调用时，才报告具体复现和适配方案。修改上游内容需要
   明确的变更来源与版本记录；不把适配后的文件冒充原始固定 commit，也不因静态告警就要求 fork。

安装报告分别列出静态告警、客户端发现和运行依赖。安装阶段没有进行业务调用时，功能状态为 `not-run`；
已确认缺少必要依赖的功能为 `blocked`。两者都不影响已经成功复制的文件安装状态。

`01` 的安装报告还单列全局建议区块状态。该区块只提醒用户考虑手动调用，并不会绕过 `disable-model-invocation: true` 或
`allow_implicit_invocation: false`，也不能作为手动调用能力已验证的证据。建议触发范围的回归用例见
[`mattpocock-skill-suggestion-tests.md`](mattpocock-skill-suggestion-tests.md)。
