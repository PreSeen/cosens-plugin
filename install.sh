#!/usr/bin/env bash
# Install the CoSens plugin into Codex and Claude Code with their own plugin commands.
#
#   curl -fsSL https://raw.githubusercontent.com/PreSeen/cosens-plugin/main/install.sh | bash
#
# Options: --target codex|claude|codex,claude (default: every client found on PATH)
#          --no-login  install only; sign in later
#
# Earlier CoSens installers left entries that take the name `cosens` or duplicate the plugin's
# skills (the old Memory plugin, its local marketplaces, a `cosens` MCP server pointing at
# memory.preseen.ai, the cosens_rsi plugin, AGENTS.md blocks). They are removed first; every file
# touched is copied, and every folder moved, into ~/.cosens-backup/<time>/. The API-key server
# `cosens_connector` is kept.
set -euo pipefail

REPO="PreSeen/cosens-plugin"
MARKET="cosens-plugin"
PLUGIN="cosens"
TARGETS=""
LOGIN=1

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGETS="${2:-}"; shift 2 ;;
    --target=*) TARGETS="${1#*=}"; shift ;;
    --no-login) LOGIN=0; shift ;;
    -h|--help) sed -n '2,14p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$TARGETS" ]; then
  command -v codex >/dev/null 2>&1 && TARGETS="codex"
  command -v claude >/dev/null 2>&1 && TARGETS="${TARGETS:+$TARGETS,}claude"
fi
[ -n "$TARGETS" ] || { echo "Neither codex nor claude is on PATH." >&2; exit 1; }

BACKUP="$HOME/.cosens-backup/$(date +%Y%m%d-%H%M%S)"
say() { printf '%s\n' "$*"; }
quiet() { "$@" 2>&1 | grep -v '^WARNING: proceeding' || true; }

backup_file() {  # copy a file into the backup, keeping its path below $HOME
  [ -f "$1" ] || return 0
  local dest="$BACKUP/${1#"$HOME"/}"
  mkdir -p "$(dirname "$dest")"
  cp -p "$1" "$dest"
}

stash() {  # move a file or folder into the backup
  [ -e "$1" ] || return 0
  local dest="$BACKUP/${1#"$HOME"/}"
  mkdir -p "$(dirname "$dest")"
  mv "$1" "$dest"
  say "  moved $1 to the backup"
}

strip_block() {  # remove <!-- NAME:start --> ... <!-- NAME:end --> from a file
  local file="$1" name="$2"
  [ -f "$file" ] && grep -q "<!-- $name:start -->" "$file" || return 0
  backup_file "$file"
  perl -0pi -e "s/\\n?<!-- \\Q$name\\E:start -->.*?<!-- \\Q$name\\E:end -->\\n?/\\n/s" "$file"
  say "  removed the $name block from $file"
}

codex_has_plugin() { codex plugin list 2>/dev/null | grep -Eq "^$1 +installed"; }
codex_has_market() { codex plugin marketplace list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$1"; }

install_codex() {
  local home="${CODEX_HOME:-$HOME/.codex}"
  say "Codex: removing earlier CoSens installs"
  backup_file "$home/config.toml"
  for p in cosens@cosens cosens@memory-connector-local cosens_rsi@cosens_connector; do
    if codex_has_plugin "$p"; then quiet codex plugin remove "$p"; say "  removed plugin $p"; fi
  done
  for m in cosens cosens_connector; do
    if codex_has_market "$m"; then quiet codex plugin marketplace remove "$m"; say "  removed marketplace $m"; fi
  done
  for s in cosens cosens_memory; do  # only entries in config.toml; the plugin's own server cannot be removed this way
    case "$(codex mcp remove "$s" 2>&1)" in *Removed*) say "  removed MCP server $s" ;; esac
  done
  stash "$home/plugins/cosens"
  stash "$home/cosens_rsi"
  stash "$home/cosens.install.json"
  if grep -qs '"memory-connector-local"' "$home/.agents/plugins/marketplace.json"; then
    stash "$home/.agents/plugins/marketplace.json"
  fi
  strip_block "$home/AGENTS.md" cosens
  strip_block "$home/AGENTS.md" cosens-rsi

  say "Codex: installing $PLUGIN@$MARKET"
  if codex_has_market "$MARKET"; then
    quiet codex plugin marketplace upgrade "$MARKET"
  else
    quiet codex plugin marketplace add "$REPO"
  fi
  quiet codex plugin add "$PLUGIN@$MARKET"
  codex_has_plugin "$PLUGIN@$MARKET" || { echo "Codex did not install $PLUGIN@$MARKET." >&2; exit 1; }

  if [ "$LOGIN" = 1 ]; then
    say "Codex: sign in to CoSens in the browser"
    quiet codex mcp logout "$PLUGIN"
    codex mcp login "$PLUGIN" </dev/tty
  fi
}

install_claude() {
  local home="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  local cfg="$HOME/.claude.json"
  [ -n "${CLAUDE_CONFIG_DIR:-}" ] && cfg="$CLAUDE_CONFIG_DIR/.claude.json"
  say "Claude Code: removing earlier CoSens installs"
  backup_file "$cfg"
  backup_file "$home/settings.json"
  for p in cosens@cosens cosens_rsi@cosens_rsi; do
    if claude plugin list 2>/dev/null | grep -q "$p\$"; then quiet claude plugin uninstall "$p"; say "  removed plugin $p"; fi
  done
  for m in cosens cosens_rsi; do
    if claude plugin marketplace list 2>/dev/null | grep -Eq "❯ $m\$"; then quiet claude plugin marketplace remove "$m"; say "  removed marketplace $m"; fi
  done
  for s in cosens cosens_memory; do
    case "$(claude mcp remove "$s" --scope user 2>&1)" in *Removed*) say "  removed MCP server $s" ;; esac
  done
  stash "$home/cosens-marketplace"
  stash "$home/cosens_rsi-marketplace"
  strip_block "$home/CLAUDE.md" cosens
  strip_block "$home/CLAUDE.md" cosens-rsi

  say "Claude Code: installing $PLUGIN@$MARKET"
  if claude plugin marketplace list 2>/dev/null | grep -Eq "❯ $MARKET\$"; then
    quiet claude plugin marketplace update "$MARKET"
  else
    quiet claude plugin marketplace add "$REPO"
  fi
  quiet claude plugin install "$PLUGIN@$MARKET"
  claude plugin list 2>/dev/null | grep -q "$PLUGIN@$MARKET\$" || { echo "Claude Code did not install $PLUGIN@$MARKET." >&2; exit 1; }

  if claude mcp get cosens_connector >/dev/null 2>&1; then
    say "  cosens_connector (API key) serves the CoSens tools; the plugin adds the skills and hooks."
  elif [ "$LOGIN" = 1 ]; then
    say "Claude Code: sign in to CoSens in the browser"
    claude mcp login "plugin:$PLUGIN:$PLUGIN" </dev/tty
  fi
}

IFS=',' read -r -a list <<<"$TARGETS"
for target in "${list[@]}"; do
  case "$target" in
    codex) command -v codex >/dev/null 2>&1 || { echo "codex is not on PATH." >&2; exit 1; }; install_codex ;;
    claude) command -v claude >/dev/null 2>&1 || { echo "claude is not on PATH." >&2; exit 1; }; install_claude ;;
    *) echo "Unknown target: $target" >&2; exit 2 ;;
  esac
done

[ -d "$BACKUP" ] && say "Backup of the files changed: $BACKUP"
say "Done. Start a new session, then ask: Use CoSens to call user_get. Do not write memory."
