# Agent Protocol test

A small study-assistant app built to learn the LangChain/LangGraph Agent Streaming Protocol before using it in the real project. There's no original design here — the backend is a direct port of the protocol's reference example, and the frontend is built on the official React SDK for it.

## What it does

You type a topic, and a LangGraph graph fans out into four chains that write notes, a quiz, a set of flashcards, and a long deep-dive essay (notes runs first; quiz and flashcards run off it in parallel; deep dive waits on both). The point isn't the study content — it's watching the protocol stream all four outputs to the browser at once, live, over one connection: token-by-token text for notes and the deep dive, and whole-object events as each quiz question or flashcard is generated.

- **`be/`** — FastAPI server. Implements the Agent Protocol's thread endpoints (`/threads`, `/threads/{id}/state`, `/threads/{id}/history`, `/threads/{id}/commands`, `/threads/{id}/stream`) around a LangGraph graph, using a `LocalThreadSession` ported from the protocol's own reference implementation (see `be/app/sessions.py`).
- **`fe/`** — Next.js app. Uses `@langchain/react`'s `StreamProvider` / `HttpAgentServerAdapter` to open the stream and `useChannel` to read specific event channels per panel (`be/app/graph.py`, `fe/app/thread/[threadId]/ThreadClient.tsx`).

## References

Everything here follows these, in the order they were useful:

- [langchain-ai/agent-protocol](https://github.com/langchain-ai/agent-protocol) — the spec itself: a framework-agnostic definition of how an agent server should expose threads, runs, streaming, and long-term state over HTTP.
- [Agent Protocol API reference](https://langchain-ai.github.io/agent-protocol/api.html#tag/runs/POST/runs/stream) — the rendered OpenAPI docs for the spec above; used to check exact request/response shapes for the streaming and thread endpoints while writing `be/app/server.py`.
- [streaming-cookbook: react-custom-backend](https://github.com/langchain-ai/streaming-cookbook/tree/main/python/react-custom-backend) — the actual template this backend is built from: a minimal Python server exposing the protocol over SSE (`LocalThreadSession`) paired with a React UI. `be/app/sessions.py` is a near-direct port of it.
- [langchain-ai/streaming-cookbook](https://github.com/langchain-ai/streaming-cookbook) — the parent repo of recipes above; used to see other streaming patterns (custom channels, transformers) beyond the one example we ported.
- [LangSmith agent-server OpenAPI spec](https://docs.langchain.com/langsmith/agent-server-openapi.json) — the full OpenAPI spec for LangGraph Platform's hosted agent server, a superset of the base protocol; used as a cross-check for how a production server implements the same endpoints.
- [`@langchain/react` reference](https://reference.langchain.com/javascript/langchain-react) — API reference for the hooks used on the frontend (`useStream`, `useChannel`, `StreamProvider`, `HttpAgentServerAdapter`).
- [langgraphjs `sdk-react` docs](https://github.com/langchain-ai/langgraphjs/tree/592fd0cab0fd9287fab1b7c7fcfd4abc44675700/libs/sdk-react/docs/) — the deeper, component-by-component usage guide for the same React SDK; used to understand channel subscriptions, submission queues, and stream context, which the reference page alone doesn't fully explain.

## Running it

Backend (needs `be/.env` — copy `be/.env.sample` and fill in `OPENAI_API_KEY`; `LANGSMITH_*` is optional):

```bash
cd be
uv sync
uv run app        # serves on http://localhost:8000
```

Frontend:

```bash
cd fe
npm install
npm run dev        # serves on http://localhost:3000
```
