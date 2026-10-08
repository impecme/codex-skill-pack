---
schema_version: 2
id: "{{NOTE_ID}}"
title: "{{PROJECT_NAME}}"
type: project
project_id: "{{PROJECT_ID}}"
repository_urls:
  - "{{REPOSITORY_URL}}"
knowledge_scopes: []
created: "{{DATE}}"
updated: "{{DATE}}"
aliases: []
---

# {{PROJECT_NAME}}

本页是项目身份、仓库映射、知识读取范围和导航的唯一权威入口。生命周期和当前工作状态由 `status.md` 维护，项目工作正文保存在 Session、决策、实验和经验记录中。

## 项目目标

{{PURPOSE}}

## 仓库与范围

- 仓库：{{REPOSITORY_URL}}
{{KNOWLEDGE_SCOPE_LINKS}}

## 项目导航

- 当前工作摘要：[[{{PATH_PROJECTS}}/{{PROJECT_ID}}/status|项目状态]]

### 最近工作记录

{{SESSION_LINKS}}

### 决策、实验与经验

{{PROJECT_KNOWLEDGE_LINKS}}

## 边界

- 源码和生成产物保留在代码仓库中。
- 本目录只保存项目上下文、决策、实验、Session 和项目经验。
- 生命周期和当前工作状态只在 `status.md` 维护；本页不复制状态正文。
