#!/usr/bin/env bash
# Runs every demo in dry mode (the agent is built, the LLM is not called).
set -euo pipefail
cd "$(dirname "$0")/.."
export GASCOIGNE_DEMO_DRY=1

for fw in langchain langgraph agno adk openai-agents crewai llamaindex pydantic-ai smolagents; do
  echo "── python / $fw"
  (cd demos/python && uv run --extra "$fw" python "${fw//-/_}_demo.py" | tail -2)
done
for d in ai-sdk langchain openai-agents mastra; do
  echo "── typescript / $d"
  (cd typescript/demos && pnpm -s "$d" | tail -2)
done
echo "── go / langchaingo"; (cd go/demos && go run ./langchaingo | tail -2)
echo "── rust"; (cd rust && cargo run -q --example logs | tail -2)
