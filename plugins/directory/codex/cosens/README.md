# CoSens

CoSens gives your agent memory across sessions and reusable Recipes for recurring work. This plugin connects your agent to the CoSens MCP server at `https://rsi.cosens.ai/mcp` and adds four skills that say when to use it: `recall`, `remember`, `document` and `workflow`.

You need a CoSens account: [request access](https://cosens.ai/request-access/). On first use, sign in through your browser and approve the connection. The plugin stores no credential.

## Try it

- "What did I decide about the release schedule for Project Aurora?"
- "Remember that Project Aurora release notes are written as a short bullet list."
- "Find a CoSens Recipe for a weekly status report and follow it."

## What is sent to CoSens

The plugin has no hooks and runs no code of its own. Data reaches CoSens only through tool calls your agent makes: the questions it recalls with, the notes you confirm, documents you authorize it to upload, and the files of a delivery you confirm for Recipe learning. Recipe learning may search the web. Uploading a local document uses the one-time `curl` command that `document_upload` returns.

See the [Privacy Policy](https://cosens.ai/privacy/), including how content is used for model training and how to delete your data.

## Troubleshooting

- A tool answers with a permission error: remove the connection, add it again and sign in.
- Recall returns nothing: a new account has no memory yet.
- Every tool appears twice: an older `cosens_connector` server is still configured; remove it.

## Support

[cosens.ai/support](https://cosens.ai/support/) or hello@cosens.ai. Terms: [cosens.ai/terms](https://cosens.ai/terms/). Documentation: [cosens.ai/docs](https://cosens.ai/docs/).
