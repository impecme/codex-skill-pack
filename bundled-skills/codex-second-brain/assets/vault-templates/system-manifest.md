---
schema_version: 2
id: "{{NOTE_ID}}"
title: "第二大脑系统清单"
type: second-brain-manifest
directory_layout: "{{DIRECTORY_LAYOUT_ID}}"
created: "{{DATE}}"
updated: "{{DATE}}"
---

# 第二大脑系统清单

本 Vault 使用 Schema 2 保存个人项目上下文和可复用知识；Vault 内的权威事实由各类型笔记分别维护。

组织灵感：`foam-inspired`。这表示借鉴链接化笔记的组织方式，不表示已安装或必须安装 Foam。
模板版本：`2`。

## 文件名约定

新建笔记文件名中的可读主题部分优先使用简体中文；顶层目录遵循本清单声明的 `directory_layout`。项目/Area/Topic ID、项目内部目录名、Schema 字段和枚举值保持 ASCII 形式。`index.md`、`status.md` 等结构文件名不翻译。既有笔记不因懒人包更新而批量改名。

## 目录说明

- `{{PATH_INBOX}}`：未整理的笔记和待复核草案。
- `{{PATH_PROJECTS}}`：项目索引、状态、Session、决策、实验和项目经验。
- `{{PATH_AREAS}}`：长期维护的责任领域。
- `{{PATH_KNOWLEDGE}}`：可复用的权威知识和主题索引。
- `{{PATH_RESOURCES}}`：外部资料和阅读笔记。
- `{{PATH_DAILY}}`：人工日期导航，不是设备自动写入目标。
- `{{PATH_ARCHIVE}}`：为保留历史而存放的非活跃内容。
- `{{PATH_SYSTEM}}`：Schema 2、模板和本清单；权威路径是 `{{PATH_SYSTEM}}/schemas/schema-v2.md` 与 `{{PATH_SYSTEM}}/templates/`。
- `{{PATH_ATTACHMENTS}}`：新建中文布局建议的附件目录；实际保存位置以 `.obsidian/app.json` 为准。保留既有附件设置，不自动修改 `.obsidian` 或移动附件。

项目源码保留在本 Vault 之外。

## 入口

- 项目集合：[[{{PATH_PROJECTS}}/index|项目集合]]
- 领域集合：[[{{PATH_AREAS}}/index|领域集合]]
- 知识集合：[[{{PATH_KNOWLEDGE}}/index|知识集合]]
- 资源集合：[[{{PATH_RESOURCES}}/index|资源集合]]
- 项目模板入口：[[{{PATH_SYSTEM}}/templates/project-index|项目索引模板]]

## 单一权威

- 项目身份、仓库映射和知识范围以项目索引为准。
- 生命周期、当前工作摘要以项目状态页为准，详细事件以 Session 为准。
- Decision、Experiment、Lesson 和 Knowledge 各自维护自己的正文；Daily 只导航，Weekly 只生成整理草案。

## 自然维护与同步

- Codex 在普通项目任务开始时只读恢复上下文，只为有持久结果的任务创建设备独立 Session。
- Daily 是人工时间导航入口，不作为多设备自动写入目标。
- Syncthing 负责设备间同步同一个主 Vault；GitHub 私有仓库只由指定设备人工备份。
- 正式知识、共享项目状态、移动删除和 Git 操作仍需确认。
