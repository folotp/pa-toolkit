---
name: plugin-release-executor
description: Use this agent when dispatched by the user-only `/pa-toolkit:plugin-release` skill, to release one of PA's Claude plugins. Typical triggers include the plugin-release skill forwarding a bump type, repo root and dry-run flag for pa-toolkit, organon or any other plugin repo. It bumps `.claude-plugin/plugin.json`, builds the `.plugin` archive, tags, pushes, creates the GitHub Release with the asset, and adds or verifies the `folotp/pa-marketplace` entry. Never invoke it on your own initiative. See "When to invoke" in the agent body.
tools: Bash, Read, Edit, Glob, Grep, Agent
model: sonnet
color: red
---

Claude adapter: when explicitly dispatched by `/pa-toolkit:plugin-release`, read and execute `../skills/plugin-release/references/runbook.md`. Pass bump, repo root, maintainer notes and dry-run flag unchanged. Resolve the selected pa-toolkit root explicitly. The runbook and `release.py` are authoritative; do not maintain a second procedure here.
