#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import select
import sys
from pathlib import Path
from typing import Any

HOOK_STATE_FILE_NAME = "cosens_hook_state.json"
STOP_MEMORY_REMINDER_CHAR_THRESHOLD = 10_000

AUTH_GUIDE_LINES = [
    "Use the configured `cosens` MCP tools directly. Authentication is managed by the MCP client's OAuth session; do not hand-craft curl or ad hoc HTTP requests for memory access. The one exception is running the upload command that `document_upload` returns.",
    "Do not pass `user_id`, `graph_id`, or `graph_ids`; ACL resolves memory scope from the authenticated OAuth identity.",
]

COMMON_TOOL_GUIDE_LINES = [
    "`user_get`: authenticated user profile and session bootstrap. Optional `query`: omit it for broad bootstrap/profile context, or pass one focused current-user profile query for preferences, hobbies, owned items, working style, or durable personal details. Without a query it returns a bounded bootstrap with sections for durable profile (长期画像), recent focus items from the last 14 days (近期重点事项), and long-running commitments (长期重要事项); with a query it returns bounded durable profile context from the authenticated user's profile scope. Personal-life memories (interests and hobbies, family, personal devices) are returned only with `include_private=true`; set it when the question is about them. It hides graph ids, ACL scope, and diagnostics. Use the durable user profile it returns as the primary source for user-profile questions such as \"who am I\", \"what are my preferences\", \"what are my hobbies\", \"what do I own\", or other long-term personal memory. Use `memory_recall(query)` for broader query-specific retrieval or exact evidence expansion.",
    "`memory_recall`: semantic retrieval and context assembly. Required `query`: one focused question with concrete anchors when available. Use it when prior decisions, preferences, project history, repository history, or cross-session state may affect the answer, especially when `user_get` is insufficient or exact evidence needs expansion. When the question has several distinct parts, recall each part with its own focused query that keeps the anchors it needs (each recall has its own token budget), then answer from all the results; a question with one part needs one recall. Stay within any cap on tool calls you were given. One focused question about one retrieval target (a person, event, decision, document or project) with the concrete anchors that identify it. Keep answer instructions, comparison criteria and guessed conclusions out of the query; apply them when you write the answer. Pass start_time/end_time only when the user stated the time range. A date you are not sure of goes neither in the query text nor in the window: the window drops memories written outside it, and dates in the query text are not read as a window. Set detailed=true when the answer combines many memories: a list, a history, a handoff or status summary of a project, or any summary across several records. When you split such a question into parts, set it on each part's recall. It returns about three times as many memories (3000 instead of 1000 estimated tokens). Leave it off for a question that one memory answers, when a default recall already answered, or under a tight token or tool-call cap. In a memory's text, what follows `summary:` is the summary of a long episode, not its original text (a sentence before `summary:` is quoted from the episode); to read the original, call memory_get with that memory's uuid (the episode uuid). Do not call memory_recall for general knowledge that is not about the user's own work, people or records; memory holds only what was written to it. If the returned memories name the specific item you are asking about (for example a ticket id, document title, or person) but do not contain the detail you need, recall again with that identifier in the query. A detail missing from one recall result is not evidence that no such record exists.",
    "`memory_get`: exact UUID drilldown. Required known `uuid`. Use it only after `memory_recall` or another trusted source gives a stable uuid for an entity, edge, episode, community, document, or thread-like object. Do not use `memory_get` for fuzzy search.",
    "`timeline_get`: exact `thread_id` timeline drilldown. Use it when recall, bootstrap, or visible context gives a concrete `thread_id` and you need the thread summary or ordered episodes. Do not use `timeline_get` without an exact `thread_id`.",
    "`recall_feedback`: report which recalled memories you used. After you answer with `memory_recall` results, call it once with one item per memory you judged: the `recall_id` of the response it came from, its `uuid`, and `used` (your answer relied on it) or `not_relevant` (you read it and judged it unrelated). Do not report memories you did not read. The call is refused as a whole when a `recall_id` is not one of your own recent recalls or a `uuid` was not in that response.",
    "`memory_write`: durable memory write. Required `data`, `type`, and `created_at`. Use it after the user confirms durable preferences, decisions, reusable project conventions, or stable summaries that should survive this session. Write concise natural-language text or message content only, preferably 1-3 sentences about one coherent assertion, decision, convention, or summary. Skip temporary tasks, logs, code snippets, one-off errors, raw transcripts, unconfirmed guesses, secrets, and large artifacts. For preferences, profile details, or working-style details about the authenticated current user, call `user_get` first when the user's display name is not already visible, then write the source sentence with that display name. Do not rewrite the current user as generic `user`, `the user`, or `用户`. Follow the MCP tool description's current target-size guidance from backend config.",
    "`document_upload`: durable document ingest. Required `filename`; the call returns a one-time `upload_url` and a `curl` command. Run that command with the local file path so the shell sends the bytes; never emit file bytes or base64. Hosts that attach files in the conversation (ChatGPT file params) fill `file` instead; the server fetches it and returns the upload result. `mime_type` is optional and inferred from filename; `uploaded_at` is optional and defaults to backend upload time. Use it for long files, PDFs, reports, meeting notes, or other document artifacts that should become searchable memory. PPTX retains slide body/table/notes/chart/OCR provenance; DOCX retains ordered blocks and OCR without invented page numbers; HTML is converted from uploaded bytes only, with no URL fetch or JavaScript execution. Legacy PPT/DOC must first be saved as PPTX/DOCX in PowerPoint, Word, or WPS. Ask before uploading local documents, screenshots, logs, or private files. Default `ingest_mode` is semantic; use graph only when relation extraction is intended and authorized.",
    "`memory_delete`: durable memory deletion. Required `uuid` and `target_type`. Use it only when the user asks for something to be removed and a previous read gave you the exact uuid. `episode` removes one memory source and whatever only it supported, which is what forgetting something means. `document` removes the uploaded file while its derived episodes stay recallable. `entity` and `edge` repair the graph and do not forget anything, because the episodes behind them remain. Deletion cannot be undone, so never delete to tidy up or to replace a memory.",
]

DEFAULT_FLOW = (
    "Default flow: `user_get` for authenticated user profile and bootstrap; for user-profile questions, "
    "answer from the durable profile first and only use `memory_recall` when the profile is insufficient. "
    "For project, repository, decision, or broader cross-session context, use `memory_recall` first, then "
    "`memory_get` or `timeline_get` for exact follow-up. After answering from `memory_recall` results, call "
    "`recall_feedback` once with the memories you used and the ones you judged not relevant. Use `memory_write` or "
    "`document_upload` only when durable persistence is appropriate."
)


def render_tool_selection_guide() -> str:
    return "\n".join(
        [
            "cosens tool selection guide:",
            *(f"- {line}" for line in [*AUTH_GUIDE_LINES, *COMMON_TOOL_GUIDE_LINES]),
            DEFAULT_FLOW,
        ]
    )


TOOL_SELECTION_GUIDE = render_tool_selection_guide()

MESSAGES = {
    "pre-tool-use": (
        "cosens: Before file reads, searches, edits, writes, shell commands, MCP calls, external "
        "writes, or document uploads, decide whether memory should constrain the action. low-risk actions "
        "with no historical dependency can proceed. If a read/search may depend on project background, "
        "directory conventions, previous decisions, or related file history, call memory_recall first and use "
        "the result to narrow the target. Before edits or writes, recall relevant project rules, accepted "
        "decisions, user preferences, and file history when they may affect the change. For shell commands, "
        "treat deletion, overwrite, install, permission, deployment, and production-affecting commands as "
        "high-risk; confirm intent or recall known run/test/deploy boundaries before proceeding. For MCP or "
        "external writes that create user-visible or irreversible effects, confirm target object, content, "
        "and impact range. Ask before uploading local documents, screenshots, logs, or private files, and "
        "do not upload material that lacks authorization or contains secrets/sensitive originals."
    ),
    "post-tool-use": (
        "cosens: Classify this tool result before continuing: no memory write, concise memory_write, "
        "or authorized document_upload. Use no memory write for temporary logs, ordinary search lists, "
        "intermediate steps, unconfirmed inferences, one-off errors, or routine file changes. Use concise "
        "memory_write only when the result confirms durable user preference, stable identity detail, team "
        "convention, project decision, accepted feedback, reusable failure cause, or other future-reusable "
        "context. Use authorized document_upload only for long documents, meeting notes, reports, PRDs, "
        "project material, screenshots/OCR material, or other file-level artifacts when the user clearly "
        "authorized long-term searchable memory. For command or test failures, including test failures, "
        "do not write immediately; debug and fix first, then write only a confirmed reusable cause or rule. "
        "Do not store secrets, tokens, passwords, sensitive originals, unauthorized local documents, "
        "temporary debug logs, one-off search results, or process-only conclusions."
    ),
    "post-compact": (
        "cosens: After context compaction, check whether prior decisions, preferences, unresolved "
        "follow-ups, accepted project rules, where to continue, or other reusable context should be preserved "
        "with memory_write. Write only confirmed durable, non-sensitive information that has not already been "
        "sent to memory_write. If nothing durable needs to be saved, continue normally without calling "
        "memory_write."
    ),
    "pre-compact": (
        "cosens: Before context compaction, check whether prior decisions, preferences, unresolved "
        "follow-ups, accepted project rules, where to continue, or other reusable context should be preserved "
        "with memory_write. Write only confirmed durable, non-sensitive information that has not already been "
        "sent to memory_write. If nothing durable needs to be saved, continue normally without calling "
        "memory_write."
    ),
    "stop": (
        "cosens: Before finishing, check whether any confirmed durable information has appeared "
        "since the last memory_write call, including user preferences, stable personal assertions, decisions, "
        "reusable conventions, accepted project rules, long-term context, or a concise confirmed continuation "
        "point for incomplete work. If yes, call memory_write now. Skip temporary tasks, logs, code snippets, "
        "one-off errors, unconfirmed guesses, sensitive originals, secrets/tokens, unauthorized documents, "
        "and duplicate memories. If nothing durable needs to be saved, finish normally without calling "
        "memory_write."
    ),
}


def _codex_home() -> Path | None:
    script_path = Path(__file__).resolve()
    try:
        return script_path.parents[3]
    except IndexError:
        return None


def _plugin_data_dir() -> Path | None:
    raw = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
    if raw and raw.strip():
        return Path(raw).expanduser()
    codex_home = _codex_home()
    if codex_home is None:
        return None
    return codex_home / "plugins" / "cosens" / "data"


def _hook_state_path() -> Path | None:
    data_dir = _plugin_data_dir()
    if data_dir is None:
        return None
    return data_dir / HOOK_STATE_FILE_NAME


def _load_hook_state() -> dict:
    path = _hook_state_path()
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_hook_state(state: dict) -> None:
    path = _hook_state_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _session_id_from_hook_input(hook_input: dict) -> str | None:
    session_id = str(hook_input.get("session_id") or "").strip()
    return session_id or None


def _session_state(state: dict, session_id: str) -> dict:
    existing = state.get(session_id)
    if isinstance(existing, dict):
        return existing
    session_state: dict = {}
    state[session_id] = session_state
    return session_state


def _stop_hook_result(hook_input: dict) -> dict | None:
    if bool(hook_input.get("stop_hook_active")):
        return None
    session_id = _session_id_from_hook_input(hook_input)
    if not session_id:
        return None

    last_assistant_message = hook_input.get("last_assistant_message")
    message_len = len(last_assistant_message) if isinstance(last_assistant_message, str) else 0

    state = _load_hook_state()
    session_state = _session_state(state, session_id)
    prior_chars = session_state.get("accumulated_chars_since_last_memory_reminder", 0)
    if not isinstance(prior_chars, int):
        prior_chars = 0
    accumulated = prior_chars + message_len
    session_state["accumulated_chars_since_last_memory_reminder"] = accumulated

    if accumulated < STOP_MEMORY_REMINDER_CHAR_THRESHOLD:
        _save_hook_state(state)
        return None

    session_state["accumulated_chars_since_last_memory_reminder"] = 0
    _save_hook_state(state)

    reason = MESSAGES["stop"]
    reason = f"{reason} When writing from this Codex session, pass thread_id: {session_id}."
    return {"decision": "block", "reason": reason}


def _candidate_tool_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, str):
        tool_name = value.strip()
        if tool_name:
            names.append(tool_name)
        return names
    if not isinstance(value, dict):
        return names

    for key in ("tool_name", "tool", "name"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            names.append(raw.strip())
    for key in ("tool_call", "tool_result", "call", "result"):
        names.extend(_candidate_tool_names(value.get(key)))
    return names


def _is_memory_write_tool_call(hook_input: dict) -> bool:
    for tool_name in _candidate_tool_names(hook_input):
        normalized = tool_name.rsplit("/", 1)[-1]
        if (
            normalized == "memory_write"
            or normalized.endswith(".memory_write")
            or normalized.endswith("__memory_write")
        ):
            return True
    return False


def _post_tool_use_result(hook_input: dict) -> None:
    session_id = _session_id_from_hook_input(hook_input)
    if not session_id or not _is_memory_write_tool_call(hook_input):
        return

    state = _load_hook_state()
    session_state = _session_state(state, session_id)
    session_state["accumulated_chars_since_last_memory_reminder"] = 0
    _save_hook_state(state)


def _read_stdin_if_available() -> str:
    try:
        if sys.stdin.closed or sys.stdin.isatty():
            return ""
        if os.name == "nt":
            return sys.stdin.read(65536)
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return ""
        return sys.stdin.read(65536)
    except (OSError, ValueError):
        return ""


def _read_hook_input() -> dict:
    raw_input = _read_stdin_if_available().strip()
    if not raw_input:
        return {}
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _session_start_context() -> str:
    lines = [
        "cosens session bootstrap:",
        "Before answering the first user request, call `cosens.user_get({})` exactly once through the configured native MCP client.",
        "Use the result as the current user's name and durable profile context. Do not expose internal graph scope, ACL data, or diagnostics.",
    ]
    workspace_lines = _workspace_anchor_lines()
    if workspace_lines:
        lines.extend(["", "Workspace anchors:", *workspace_lines])
    return "\n".join(lines)


def _additional_context_payload(event_name: str, context: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    }


def _workspace_anchor_lines() -> list[str]:
    lines: list[str] = []
    try:
        cwd = Path.cwd()
    except OSError:
        return lines
    lines.append(f"- cwd: {cwd}")
    repo_root = _find_repo_root(cwd)
    if repo_root is not None:
        lines.append(f"- repo_root: {repo_root}")
        lines.append(f"- project: {repo_root.name}")
    else:
        lines.append(f"- project: {cwd.name}")
    codex_workspace = os.environ.get("CODEX_WORKSPACE") or os.environ.get("PWD")
    if codex_workspace and codex_workspace != str(cwd):
        lines.append(f"- workspace_hint: {codex_workspace}")
    return lines


def _find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    if event == "session-start":
        print(
            json.dumps(
                _additional_context_payload("SessionStart", _session_start_context()),
                ensure_ascii=False,
            )
        )
        return 0
    if event == "stop":
        result = _stop_hook_result(_read_hook_input())
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    if event == "post-tool-use":
        _post_tool_use_result(_read_hook_input())
        return 0
    message = MESSAGES.get(event)
    if not message:
        return 0
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
