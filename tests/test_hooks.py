"""The PreToolUse hook records the host session on memory_write without making a Thread."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "source" / "scripts" / "emit_system_message.py"


def run(host, payload):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "record-session", host], input=json.dumps(payload),
        capture_output=True, text=True, check=True,
    )
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else None


class RecordSession(unittest.TestCase):
    call = {"data": "记" * 40000, "type": "text", "created_at": "2026-01-01T00:00:00Z"}

    def updated(self, tool_input):
        return run("claude", {"session_id": "sess-1", "tool_input": tool_input})["updatedInput"]

    def test_session_is_recorded_and_no_thread_is_made(self):
        out = self.updated(self.call)
        self.assertEqual(out, {**self.call, "source": {"extra": {"session_id": "sess-1"}}})
        self.assertNotIn("thread_id", out)

    def test_the_callers_source_and_thread_id_are_kept(self):
        given = {**self.call, "thread_id": "chosen", "source": {"type": "meeting", "id": "m1", "extra": {"room": "a"}}}
        out = self.updated(given)
        self.assertEqual(out["thread_id"], "chosen")
        self.assertEqual(out["source"], {"type": "meeting", "id": "m1", "extra": {"room": "a", "session_id": "sess-1"}})

    def test_claude_keeps_its_permission_prompt_and_codex_needs_allow(self):
        payload = {"session_id": "s", "tool_input": self.call}
        self.assertNotIn("permissionDecision", run("claude", payload))
        self.assertEqual(run("codex", payload)["permissionDecision"], "allow")

    def test_no_session_leaves_the_call_alone(self):
        self.assertIsNone(run("codex", {"tool_input": self.call}))

    def test_both_hosts_match_their_memory_write_tool_name(self):
        for host, name in (("claude", "mcp__plugin_cosens_cosens__memory_write"), ("codex", "mcp__cosens__memory_write")):
            hooks = json.loads((ROOT / "source" / "hooks" / f"hooks.{host}.json").read_text())["hooks"]
            entry = hooks["PreToolUse"][0]
            self.assertRegex(name, re.compile(entry["matcher"]))
            self.assertNotRegex(name.replace("write", "delete"), re.compile(entry["matcher"]))
            self.assertTrue(entry["hooks"][0]["command"].endswith(f"record-session {host}"))


class ToolGuide(unittest.TestCase):
    def test_user_get_sections_are_described_without_chinese_heading_names(self):
        """CoSens returns English section titles; the guide must not name other ones."""
        for relative in ("scripts/emit_system_message.py", "skills/recall/SKILL.md", "skills/document/SKILL.md"):
            text = (ROOT / "source" / relative).read_text(encoding="utf-8")
            lines = [line for line in text.splitlines() if "`user_get`: authenticated user profile" in line]
            self.assertTrue(lines, relative)
            for line in lines:
                self.assertNotRegex(line, "[\u4e00-\u9fff]", relative)


if __name__ == "__main__":
    unittest.main()
