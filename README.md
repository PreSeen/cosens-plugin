# CoSens plugin

The official CoSens plugin for Claude and Codex. It connects your agent to CoSens through one MCP server, `https://rsi.cosens.ai/mcp`, and adds skills that tell the agent when to use it:

| Skill | What it does |
| --- | --- |
| `recall` | Looks up your past decisions, preferences, people and documents before substantial work. |
| `remember` | Saves a short, confirmed, durable decision or preference. |
| `document` | Uploads a long file you authorize so it becomes searchable memory. |
| `workflow` | Finds a reusable Recipe before a task, and lets CoSens learn a new version from a delivery you confirm. |

In Claude Code and Codex the plugin also adds session hooks: a memory bootstrap at session start, and a reminder to keep durable context before compaction and before finishing. Claude chat ignores hooks.

You need a CoSens account. [Request access](https://cosens.ai/request-access/).

## Install

### Claude (web, desktop and Cowork)

1. Open **Customize → Plugins → Add → Add marketplace** and enter `PreSeen/cosens-plugin`.
2. Select **CoSens** and **Add**.
3. Open the plugin's **Connectors** tab and connect **cosens**. Sign in with your CoSens account and approve.

To install without the marketplace, download `cosens-claude-<version>.zip` from [Releases](https://github.com/PreSeen/cosens-plugin/releases) and use **Add → Upload plugin**.

A plugin added in Claude is saved to your account, so it also appears in Claude Code when you sign in with the same account.

### Claude Code

```text
/plugin marketplace add PreSeen/cosens-plugin
/plugin install cosens@cosens-plugin
```

Then run `/mcp`, select `plugin:cosens:cosens` and choose **Authenticate**.

### Codex

```bash
codex plugin marketplace add PreSeen/cosens-plugin
codex plugin add cosens@cosens-plugin
codex mcp login cosens
```

## Sign-in and the RSI tools

The plugin signs in with OAuth in the browser and stores no credential. OAuth sign-in currently gives the Memory tools only; the RSI tools answer with a permission error. To use RSI from Claude Code or Codex today, use the [CoSens installer](https://cosens.ai/docs/), which stores an API key, instead of this plugin. Do not use both: the installer registers its own `cosens_connector` server, and the agent would see every tool twice.

## Check the connection

Ask the agent:

```text
Use CoSens to call user_get. Do not write memory.
```

## Repository layout

```text
source/                          the only place to edit
  plugin.json                    name, version and descriptions for every client
  mcp.json                       the CoSens MCP server
  skills/  hooks/  scripts/  assets/
plugins/claude/cosens/           generated Claude plugin
plugins/codex/cosens/            generated Codex plugin
.claude-plugin/marketplace.json  generated Claude marketplace
.agents/plugins/marketplace.json generated Codex marketplace
scripts/build.py                 generates the above; --check verifies, --zip builds the upload archive
```

After editing `source/`, run `python3 scripts/build.py` and commit the generated files. CI runs `python3 scripts/build.py --check`. To release, bump `version` in `source/plugin.json`, run `python3 scripts/build.py --zip`, and attach `dist/cosens-claude-<version>.zip` to a GitHub release.

The Memory skills and the hook script follow the Memory service's tool guidance (`PreSeen/friday-memory`, `backend/app/mcp_agent_guidance.py`); update them here when that guidance changes.

## Support

Documentation: [cosens.ai/docs](https://cosens.ai/docs/). Privacy: [cosens.ai/privacy](https://cosens.ai/privacy/). Terms: [cosens.ai/terms](https://cosens.ai/terms/).
