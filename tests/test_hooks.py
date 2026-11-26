"""The PreToolUse hook fills memory_write's thread_id with the host session id."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "source" / "scripts" / "emit_system_message.py"


def run(event, host, payload):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), event, host], input=json.dumps(payload),
        capture_output=True, text=True, check=True,
    )
    return json.loads(done.stdout) if done.stdout.strip() else None


class FillThreadId(unittest.TestCase):
    payload = {
        "session_id": "sess-1",
        "tool_input": {"data": "记" * 40000, "type": "text", "created_at": "2026-01-01T00:00:00Z", "thread_id": "made-up"},
    }

    def test_every_argument_is_kept_and_thread_id_is_the_session(self):
        out = run("fill-thread-id", "claude", self.payload)["hookSpecificOutput"]
        self.assertEqual(out["updatedInput"], {**self.payload["tool_input"], "thread_id": "sess-1"})

    def test_claude_keeps_its_permission_prompt(self):
        self.assertNotIn("permissionDecision", run("fill-thread-id", "claude", self.payload)["hookSpecificOutput"])

    def test_codex_needs_allow_with_the_rewrite(self):
        self.assertEqual(run("fill-thread-id", "codex", self.payload)["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_no_session_leaves_the_call_alone(self):
        self.assertIsNone(run("fill-thread-id", "codex", {"tool_input": {"data": "x"}}))

    def test_both_hosts_match_their_memory_write_tool_name(self):
        for host, name in (("claude", "mcp__plugin_cosens_cosens__memory_write"), ("codex", "mcp__cosens__memory_write")):
            hooks = json.loads((ROOT / "source" / "hooks" / f"hooks.{host}.json").read_text())["hooks"]
            entry = hooks["PreToolUse"][0]
            self.assertRegex(name, re.compile(entry["matcher"]))
            self.assertNotRegex(name.replace("write", "delete"), re.compile(entry["matcher"]))
            self.assertTrue(entry["hooks"][0]["command"].endswith(f"fill-thread-id {host}"))


if __name__ == "__main__":
    unittest.main()
