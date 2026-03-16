# MemWire Docs

Documentation for [MemWire](https://github.com/memoryoss/memwire) — enterprise-grade, self-hosted AI memory infrastructure layer.

Built with [Mintlify](https://mintlify.com). Live at [memwirelabs.ai](https://memwirelabs.ai).

## Structure

```
docs/
├── docs.json                  # Mintlify config (navigation, colors, branding)
├── index.mdx                  # Introduction page
├── quickstart.mdx             # Python SDK quickstart
├── api-reference/
│   ├── introduction.mdx       # REST API overview
│   └── endpoint/
│       ├── store.mdx          # POST /v1/memories
│       ├── recall.mdx         # POST /v1/memories/recall
│       └── search.mdx         # POST /v1/memories/search

examples/
├── chat.py                    # Terminal chat demo (OpenAI)
├── chat_azure.py              # Terminal chat demo (Azure OpenAI)
├── web_chat.py                # Browser chat demo (OpenAI)
├── web_chat_azure.py          # Browser chat demo (Azure OpenAI)
├── Dockerfile                 # Builds web_chat.py server
└── docker-compose.yml         # Qdrant + MemWire server
```

## Local preview

Install the Mintlify CLI:

```bash
npm i -g mint
```

Run from the `docs/` directory:

```bash
mint dev
```

Preview at `http://localhost:3000`.

## Publishing

Push to the `main` branch — the Mintlify GitHub app deploys automatically.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) in the root of the repo.
