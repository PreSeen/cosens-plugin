---
name: remember
description: Save short, confirmed-durable preferences, decisions, conventions, and summaries to cosens with memory_write.
---

# Remember

Use this when the conversation produces short, durable context that should outlive this session. Use it for short non-document memory. For file-level material (long files, PDFs, reports, notes, screenshots, logs) use the `document` skill instead.

Write with `memory_write` only when something is confirmed durable:

- stable user preferences or working style
- confirmed decisions and their rationale
- long-lived project conventions
- a status that supersedes an older durable relation
- a concise summary of important completed work

`wait_for_processing`: Leave it false unless the next step needs the relations extracted from this write: the call returns after the episode is saved, and its sentences are indexed for recall within seconds, while extraction usually takes one to a few minutes, so a wait normally ends at wait_timeout_seconds and only delays the reply.

Keep it to one short, distilled natural-language relation or summary — never a raw transcript. Use the original source time for `created_at`, not the current time. When writing about the authenticated user, call `user_get` first (if their display name isn't already visible) and name them — don't flatten them to a generic "user" / "用户".

Never write secrets, tokens, one-off logs, debug chatter, unconfirmed guesses, sensitive originals, or unauthorized content. For long artifacts, use the document skill.
