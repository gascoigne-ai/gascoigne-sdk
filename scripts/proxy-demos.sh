#!/usr/bin/env bash
# Runs the proxy-mode demos for real, with no API key: a fake LLM (scripts/fake_llm.py) stands in
# for OpenRouter, and a dedicated gascoigne server forwards to it.
set -euo pipefail
cd "$(dirname "$0")/.."

port=8091
config=$(mktemp --suffix=.yaml)
ledger=$(mktemp --suffix=.db)
printf 'receivers:\n  httpproxy:\n    openai: http://127.0.0.1:%s\n' "$port" > "$config"

python3 scripts/fake_llm.py "$port" &
fake=$!
trap 'kill $fake 2>/dev/null; rm -f "$config" "$ledger"' EXIT
sleep 1

export GASCOIGNE_CONFIG=$config GASCOIGNE_LEDGER=$ledger GASCOIGNE_SERVER_ADDR=127.0.0.1:7874
export OPENROUTER_API_KEY=fake
unset GASCOIGNE_DEMO_DRY

for demo in langchain langgraph agno google-adk openai-agents crewai llamaindex pydantic-ai; do
  echo "-- python / $demo (proxy)"
  extra=${demo/google-adk/adk}
  (cd demos/python && uv run --extra "$extra" python "$demo/proxy.py" | grep -E "search_logs \||Bypassed")
done
for demo in ai-sdk langchain openai-agents mastra; do
  echo "-- typescript / $demo (proxy)"
  (cd typescript/demos && pnpm -s "proxy:$demo" | grep -E "search_logs:|no new")
done
echo "-- java / spring-ai (proxy)"
(cd java/demos && java -jar spring-ai-proxy/target/demo-spring-ai-proxy-0.0.0.jar | grep -E "search_logs:|no new")
