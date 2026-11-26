# CoSens plugin

The official CoSens plugin for Claude and Codex. It connects your agent to CoSens through one MCP server, `https://rsi.cosens.ai/mcp`, and adds skills that tell the agent when to use it:

| Skill | What it does |
| --- | --- |
| `recall` | Looks up your past decisions, preferences, people and documents before substantial work. |
| `remember` | Saves a short, confirmed, durable decision or preference. |
| `document` | Uploads a long file you authorize so it becomes searchable memory. |
| `workflow` | Finds a reusable Recipe before a task, and lets CoSens learn a new version from a delivery you confirm. |

In Claude Code and Codex the plugin also adds session hooks: a memory bootstrap at session start, and a reminder to keep durable context before compaction and before finishing. Before `memory_write`, a hook fills `thread_id` with the session id, so memories from one session stay linked. Claude chat ignores hooks.

You need a CoSens account. [Request access](https://cosens.ai/request-access/).

## Install

The [CoSens Console](https://console.cosens.ai/) shows the steps for each client under **Connect an agent**.

### One command for Codex and Claude Code

```bash
curl -fsSL https://rsi.cosens.ai/api/agent/install | bash
```

CoSens serves this installer (source: `src/cosens_rsi/static/install-plugin.sh` in the CoSens RSI service). It runs the clients' own plugin commands shown below for every client it finds (`--target codex` or `--target claude` to pick one), then opens the browser to sign in (`--no-login` to skip). If an earlier CoSens installer was used on the machine, it first removes what that installer left, which would otherwise take the `cosens` name or duplicate the tools and skills. Every file it changes is copied, and every folder it removes is moved, into `~/.cosens-backup/<time>/`.

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

Earlier CoSens installers registered a `cosens_connector` server with an API key. Keeping it next to the plugin shows every tool twice; the one-command installer above removes it.

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
plugins/directory/               generated public-directory packages (no hooks)
.claude-plugin/marketplace.json  generated Claude marketplace
.agents/plugins/marketplace.json generated Codex marketplace
scripts/build.py                 generates the above; --check verifies, --zip builds the upload archive
```

After editing `source/`, run `python3 scripts/build.py` and commit the generated files. CI runs `python3 scripts/build.py --check`. To release, bump `version` in `source/plugin.json`, run `python3 scripts/build.py --zip`, and attach `dist/cosens-claude-<version>.zip` to a GitHub release.

The Memory skills and the hook script follow the Memory service's tool guidance; update them here when that guidance changes.

## Public directories

The packages under `plugins/directory/` are the ones submitted to the Claude and OpenAI plugin directories. They carry no hooks. `scripts/build.py --zip` also writes the OpenAI upload archive. The OpenAI review test cases are in `source/directory/codex-review.json`.

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Support

Documentation: [cosens.ai/docs](https://cosens.ai/docs/). Privacy: [cosens.ai/privacy](https://cosens.ai/privacy/). Terms: [cosens.ai/terms](https://cosens.ai/terms/).
