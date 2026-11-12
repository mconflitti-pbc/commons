# Commons A2A agents

These are two data agents for Posit Connect. Each one answers questions over an Agent2Agent (A2A) JSON-RPC endpoint. Each agent is a Commons agent, built per A2A context on the first message.

- `sales/` serves the **Sales data agent**. It answers questions about 480 synthetic sales orders. It has a `revenue` measure.
- `hospital/` serves the **Hospital operations agent**. It answers questions about 10,000 synthetic hospital event records. It has the `hospital_summary` and `hospital_event_counts` measures.

Each folder is self-contained. It holds its own app, measures, data, instructions, requirements, and the Commons wheel. Deploy one folder as one Connect content item.

The data is synthetic and is for demonstration only.

## Layout

```text
sales/
  app.py                 # exposes `app` (FastAPI), built with create_a2a_app
  measures.py            # trusted measures
  instructions.md        # additional instructions for the agent
  requirements.txt
  commons-<version>-py3-none-any.whl   # not tracked; see "Build the Commons wheel"
  data/                  # orders.parquet, data-dict.yaml, context.md
hospital/
  (same layout; data/hospital_events.parquet)
```

## Requirements

- Python 3.11 or later. Commons requires it.
- `uv`, to build the wheel and run local checks.
- The `posit-sdk` commit that `requirements.txt` pins, pushed to GitHub. The commit is on the branch `mconflitti-pbc/commons-helpers`.
- On Connect, an Anthropic integration attached to each content item.

## Build the Commons wheel

Each folder needs a Commons wheel. Build it from `pkg-py/`, then copy it into both folders:

```bash
cd pkg-py
uv build --wheel
cp dist/commons-0.1.0b2-py3-none-any.whl examples/a2a-agents/sales/
cp dist/commons-0.1.0b2-py3-none-any.whl examples/a2a-agents/hospital/
```

The wheel is not tracked. This folder's `.gitignore` ignores `*.whl` files and `rsconnect-python/`. Do not commit the wheel. If the Commons version changes, rebuild the wheel and update the `./commons-<version>-py3-none-any.whl` line in both `requirements.txt` files.

## Run locally

Run these commands from one app folder, for example `sales/`. The SDK line in `requirements.txt` needs the pushed branch. Before the branch is pushed, replace that line with a path to a local `posit_sdk` wheel.

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # your own key, for real answers only
uv run uvicorn app:app --port 8000
```

Without `ANTHROPIC_API_KEY`, the server still starts. Each question then returns a failed task, and the server logs the reason.

Fetch the agent card:

```bash
curl -s http://127.0.0.1:8000/.well-known/agent-card.json
```

Send a question:

```bash
curl -s -X POST http://127.0.0.1:8000/a2a/jsonrpc \
  -H "A2A-Version: 1.0" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"What was total revenue?"}]}}}'
```

## Deploy

Before you deploy a folder, check that it holds the wheel. If it does not, build the wheel first. See [Build the Commons wheel](#build-the-commons-wheel).

Deploy each folder as its own content item. Run these commands from the repository root. Install `rsconnect-python` with `uvx`, as shown. If the `CONNECT_SERVER` variable is set, unset it. rsconnect rejects `-n` together with that variable.

```bash
uvx --from rsconnect-python rsconnect deploy fastapi -n <server> \
  --entrypoint app:app --title "Sales data agent" pkg-py/examples/a2a-agents/sales

uvx --from rsconnect-python rsconnect deploy fastapi -n <server> \
  --entrypoint app:app --title "Hospital operations agent" pkg-py/examples/a2a-agents/hospital
```

After each deploy, attach the Anthropic integration to the content in the Connect UI. Connect sets `ANTHROPIC_API_KEY` and, when the integration uses the AI Gateway, `ANTHROPIC_BASE_URL`. If the content was already running before you attached the integration, restart it so the variables reach the process. This restart step is unverified.

The agent card is at:

```text
<server>/content/<guid>/.well-known/agent-card.json
```

The JSON-RPC endpoint is at `<server>/content/<guid>/a2a/jsonrpc`.

## Environment variables

| Variable | Set by | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Connect (Anthropic integration), or you locally | Required for answers. The app does not set it. |
| `ANTHROPIC_BASE_URL` | Connect (AI Gateway), optional | Overrides the Anthropic endpoint. The app does not set it. |
| `COMMONS_CHAT_MODEL` | You, optional | Model name. Default `anthropic/claude-sonnet-5`. |
| `COMMONS_ALLOW_UNSAFE_FALLBACK` | You, optional | Set to `1` only when Connect lacks Landlock and user namespaces. See the sandbox note. Demo data only. |
| `CONNECT_SERVER`, `CONNECT_CONTENT_GUID` | Connect | Used to build the URLs on the agent card. |

## Sandbox note

When the model runs Python code, Commons runs that code in a sandboxed worker process. On Linux, the sandbox needs Landlock or unprivileged user namespaces. If the host has neither, creating an agent raises a `RuntimeError`, and every question fails. In that case, set `COMMONS_ALLOW_UNSAFE_FALLBACK=1` on the content item. That setting turns off the sandbox checks. Use it only with this demo data.

## Attach integrations

- **Anthropic:** attach the Anthropic integration to each content item. Without it, the agent cannot answer.

## Resource use

Each A2A context builds its own agent. The app keeps up to 100 contexts in memory by default, and evicts the least recently used one. The agent also registers a `run_python` tool. When the model uses it, a sandboxed Python process starts for that context.
