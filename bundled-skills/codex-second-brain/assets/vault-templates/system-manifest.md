---
schema_version: 2
id: "{{NOTE_ID}}"
title: "第二大脑系统清单"
type: second-brain-manifest
created: "{{DATE}}"
updated: "{{DATE}}"
---

# 第二大脑系统清单

本 Vault 使用 Schema 2 保存个人项目上下文和可复用知识；Vault 内的权威事实由各类型笔记分别维护。

组织灵感：`foam-inspired`。这表示借鉴链接化笔记的组织方式，不表示已安装或必须安装 Foam。
模板版本：`2`。

## 目录说明

- `00-Inbox`：未整理的笔记和待复核草案。
- `10-Projects`：项目索引、状态、Session、决策、实验和项目经验。
- `20-Areas`：长期维护的责任领域。
- `30-Knowledge`：可复用的权威知识和主题索引。
- `40-Resources`：外部资料和阅读笔记。
- `50-Daily`：人工日期导航，不是设备自动写入目标。
- `60-Archive`：为保留历史而存放的非活跃内容。
- `90-System`：Schema 2、模板和本清单；权威路径是 `90-System/schemas/schema-v2.md` 与 `90-System/templates/`。

项目源码保留在本 Vault 之外。

## 入口

- 项目集合：[[10-Projects/index|项目集合]]
- 领域集合：[[20-Areas/index|领域集合]]
- 知识集合：[[30-Knowledge/index|知识集合]]
- 资源集合：[[40-Resources/index|资源集合]]
- 项目模板入口：[[90-System/templates/project-index|项目索引模板]]

## 单一权威

- 项目身份、仓库映射和知识范围以项目索引为准。
- 生命周期、当前工作摘要以项目状态页为准，详细事件以 Session 为准。
- Decision、Experiment、Lesson 和 Knowledge 各自维护自己的正文；Daily 只导航，Weekly 只生成整理草案。

## 自然维护与同步

- Codex 在普通项目任务开始时只读恢复上下文，只为有持久结果的任务创建设备独立 Session。
- Daily 是人工时间导航入口，不作为多设备自动写入目标。
- Syncthing 负责设备间同步同一个主 Vault；GitHub 私有仓库只由指定设备人工备份。
- 正式知识、共享项目状态、移动删除和 Git 操作仍需确认。
