#!/usr/bin/env python3
"""Generate the per-client plugin packages and the marketplace catalogs from source/.

source/ is the only place to edit. This script writes:
  plugins/claude/cosens/   Claude plugin (Claude apps, Cowork, Claude Code)
  plugins/codex/cosens/    Codex plugin
  .claude-plugin/marketplace.json, .agents/plugins/marketplace.json
and, with --zip, dist/cosens-claude-<version>.zip for Customize > Plugins > Upload plugin.

--check regenerates in memory and fails if a committed file differs, so CI catches
an edit made to a generated file instead of to source/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source"
MARKETPLACE = "cosens-plugin"
OWNER = {"name": "PreSeen AI", "url": "https://cosens.ai"}
SHARED = ("skills", "scripts", "assets")


def dump(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def meta() -> dict:
    return json.loads((SOURCE / "plugin.json").read_text(encoding="utf-8"))


def claude_manifest(m: dict) -> dict:
    return {
        "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
        "name": m["name"],
        "displayName": m["displayName"],
        "version": m["version"],
        "description": m["description"],
        "author": m["author"],
        "homepage": m["homepage"],
        "repository": m["repository"],
        "keywords": m["keywords"],
        "license": m["license"],
        "icon": "./assets/logo.svg",
        "privacyPolicyUrl": m["privacyPolicyUrl"],
        "termsOfServiceUrl": m["termsOfServiceUrl"],
        "documentationUrl": m["homepage"],
    }


def codex_manifest(m: dict) -> dict:
    return {
        "name": m["name"],
        "version": m["version"],
        "description": m["description"],
        "author": m["author"],
        "homepage": m["homepage"],
        "repository": m["repository"],
        "keywords": m["keywords"],
        "license": m["license"],
        "skills": "./skills/",
        "mcpServers": "./.mcp.json",
        "hooks": "./hooks/hooks.json",
        "interface": {
            "displayName": m["displayName"],
            "shortDescription": m["shortDescription"],
            "longDescription": m["longDescription"],
            "developerName": m["author"]["name"],
            "category": m["category"],
            "capabilities": ["Read", "Write"],
            "websiteURL": m["homepage"],
            "privacyPolicyURL": m["privacyPolicyUrl"],
            "termsOfServiceURL": m["termsOfServiceUrl"],
            "defaultPrompt": m["defaultPrompt"],
            "composerIcon": "./assets/logo.svg",
            "logo": "./assets/logo.svg",
            "brandColor": m["brandColor"],
        },
    }


def write_plugin(dest: Path, host: str, m: dict) -> None:
    for name in SHARED:
        shutil.copytree(SOURCE / name, dest / name, ignore=shutil.ignore_patterns("__pycache__"))
    (dest / "hooks").mkdir(parents=True)
    shutil.copyfile(SOURCE / "hooks" / f"hooks.{host}.json", dest / "hooks" / "hooks.json")
    shutil.copyfile(SOURCE / "mcp.json", dest / ".mcp.json")
    shutil.copyfile(ROOT / "LICENSE", dest / "LICENSE")
    manifest_dir = dest / (".claude-plugin" if host == "claude" else ".codex-plugin")
    manifest_dir.mkdir()
    manifest = claude_manifest(m) if host == "claude" else codex_manifest(m)
    (manifest_dir / "plugin.json").write_text(dump(manifest), encoding="utf-8")


def generate(out: Path) -> None:
    m = meta()
    write_plugin(out / "plugins" / "claude" / m["name"], "claude", m)
    write_plugin(out / "plugins" / "codex" / m["name"], "codex", m)
    claude_catalog = {
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": MARKETPLACE,
        "description": "CoSens plugins for Claude.",
        "owner": OWNER,
        "plugins": [
            {
                "name": m["name"],
                "displayName": m["displayName"],
                "source": f"./plugins/claude/{m['name']}",
                "description": m["description"],
                "version": m["version"],
                "category": m["category"].lower(),
                "homepage": m["homepage"],
                "author": m["author"],
            }
        ],
    }
    codex_catalog = {
        "name": MARKETPLACE,
        "interface": {"displayName": m["displayName"]},
        "plugins": [
            {
                "name": m["name"],
                "source": {"source": "local", "path": f"./plugins/codex/{m['name']}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": m["category"],
            }
        ],
    }
    (out / ".claude-plugin").mkdir(parents=True)
    (out / ".claude-plugin" / "marketplace.json").write_text(dump(claude_catalog), encoding="utf-8")
    (out / ".agents" / "plugins").mkdir(parents=True)
    (out / ".agents" / "plugins" / "marketplace.json").write_text(dump(codex_catalog), encoding="utf-8")


GENERATED = ("plugins", ".claude-plugin", ".agents")


def files(base: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for top in GENERATED:
        for path in sorted((base / top).rglob("*")) if (base / top).exists() else []:
            if path.is_file() and "__pycache__" not in path.parts:
                found[path.relative_to(base).as_posix()] = path.read_bytes()
    return found


def build_zip(m: dict) -> Path:
    plugin = ROOT / "plugins" / "claude" / m["name"]
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    target = dist / f"{m['name']}-claude-{m['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(plugin.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(plugin).as_posix())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if committed generated files are stale")
    parser.add_argument("--zip", action="store_true", help="also write the Claude upload archive to dist/")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        expected = files(Path(tmp))
        if args.check:
            actual = files(ROOT)
            stale = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
            if stale:
                print("Generated files are stale; run scripts/build.py:", *stale, sep="\n  ", file=sys.stderr)
                return 1
            print(f"OK: {len(expected)} generated files match source/")
            return 0
        for top in GENERATED:
            shutil.rmtree(ROOT / top, ignore_errors=True)
            if (Path(tmp) / top).exists():
                shutil.copytree(Path(tmp) / top, ROOT / top)
    print(f"Wrote {len(expected)} files")
    if args.zip:
        print(f"Wrote {build_zip(meta()).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
