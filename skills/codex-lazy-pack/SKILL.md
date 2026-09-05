---
name: codex-lazy-pack
description: Install, inspect, or repair this pinned personal Codex environment through a conversation, using explicit confirmation before changing user-level configuration.
---

# Codex Lazy Pack

Use this skill when the user asks to install, inspect, repair, or verify this personal lazy pack.
The installation is conversation-driven: inspect the lock file, explain the changes, use the
available Codex installation and file tools, and report each result. Do not look for or execute a
PowerShell/Shell bootstrap script.

## Installation contract

- Read `sources.lock.json` before making changes.
- Install the complete pinned Luna/Sol workflow and all 18 Engineering skills listed there.
- Keep the source commits fixed. If the available skill installer cannot install a commit-pinned
  directory, fetch the exact commit contents with the available file or repository tools instead of
  silently falling back to a branch head.
- Read [conversation-install.md](references/conversation-install.md) for target mappings and the
  exact source paths.
- Treat changes under the user's Codex home as consequential. Inspect existing files, show useful
  differences, back up before replacement, and ask the user to choose merge, replace, or skip.
- Do not install unlisted plugins, MCP servers, credentials, GitHub authentication, or unrelated
  skills.

## Conversation flow

1. Summarize the two pinned sources, the 4 workflow files, the 18 skill names, and target paths.
2. Confirm that the user wants the complete locked set unless that choice was already explicit in
   the conversation.
3. Check the current Codex home and skill directory, including existing same-name skills and
   configuration.
4. Install the requested items using the host's available Codex skill/file tools.
5. For every conflict, present the relevant diff and wait for a merge, replace, or skip decision.
6. Report installed, already-current, skipped, conflicted, and failed items separately. Include
   backups and any manual follow-up.

The pack is personal and general-purpose. It should not be described as an operator-specific pack.
