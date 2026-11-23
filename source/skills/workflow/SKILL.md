---
name: workflow
description: Use the CoSens RSI tools to reuse Recipes before a task and let CoSens learn from deliveries the user confirmed.
---

# CoSens RSI Workflow

Use the configured `cosens` MCP tools. The client supplies the credentials; never ask for or handle an API key yourself.

- At the start of a task, use `rsi_recipe_list` to find a Recipe for this kind of work and `rsi_recipe_get` to read its active version's instructions. Follow them; the actual execution belongs to you, the host.
- Only after the user confirms a delivery, call `rsi_execution_create` with the `context` (the conversation or task as one file), the evidence `files` and a stable `idempotency_key`. Give each file a `role`: `input` (the task input, also used to replay the task), `artifact` (the confirmed deliverable), `reference` (shared material), `feedback` (the user's own requirements or corrections; never your own judgement) or `recipe` (the Recipe you followed, with its `recipe_id`, at most one). CoSens learns in the background: it extracts the feedback, writes Rubrics and a Recipe version, replays the task, scores the result and publishes a passing version.
- Poll `rsi_execution_get` for status, stage, progress, clarification questions and test results. Ask the user each clarification question and send their answer with `rsi_execution_clarification_answer`; when the result names a `continuation_execution_id`, follow that execution.
- Use `rsi_execution_append_evidence` to add evidence to a running execution, `rsi_execution_cancel` to stop a queued or running one, and `rsi_execution_list` to list executions.
- Use `rsi_rubrics_list` and `rsi_rubrics_get` to read Rubrics, and `rsi_recipe_test` to test a Recipe version against an active execution's task with a given Rubrics version.
- When the user hands you a Recipe they wrote, upload it with `rsi_recipe_insert`: send the whole file as `markdown` in the Skill format (YAML frontmatter with nonempty `name` and `description`, then the instructions). It becomes a new Recipe whose v1 is available at once.

If an `rsi_*` tool answers with a permission error, the connection was authorized before RSI access was available: say so, and ask the user to remove the CoSens connector, add it again and sign in. Do not retry the call.

Report installation, connectivity and operation results separately. Do not invent execution, Recipe or Rubrics IDs. Do not supply identity or graph selectors.
