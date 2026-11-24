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

### One command for Codex and Claude Code

```bash
curl -fsSL https://raw.githubusercontent.com/PreSeen/cosens-plugin/main/install.sh | bash
```

It runs the clients' own plugin commands shown below for every client it finds (`--target codex` or `--target claude` to pick one), then opens the browser to sign in (`--no-login` to skip). If an earlier CoSens installer was used on the machine, it first removes what that installer left (the old Memory plugin and its local marketplaces, a `cosens` MCP server pointing at `memory.preseen.ai`, the `cosens_rsi` plugin and its `AGENTS.md` blocks), which would otherwise take the `cosens` name or duplicate the skills. Every file it changes is copied, and every folder it removes is moved, into `~/.cosens-backup/<time>/`. It keeps an existing `cosens_connector` (API key) server.

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

The plugin signs in with OAuth in the browser and stores no credential. The consent page lists what the connection may do: read and write your memory, upload documents, and read and create Recipes and runs in RSI. After you approve, both the Memory and the RSI tools work.

A connection authorized before RSI access was available holds Memory permissions only, and its RSI tools answer with a permission error. Remove the connector (or uninstall the plugin), add it again and sign in; the new connection asks for RSI access too.

Do not install the plugin next to the [CoSens installer](https://cosens.ai/docs/), which registers its own `cosens_connector` server with an API key: the agent would see every tool twice.

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
