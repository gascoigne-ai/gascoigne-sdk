#!/usr/bin/env bash
# Runs the proxy and auto demos for real, with no API key. A fake LLM (scripts/fake_llm.py) stands
# in for OpenRouter; a dedicated gascoigne server forwards to it.
set -euo pipefail
cd "$(dirname "$0")/.."

# Fresh ports every run: a server left over from an earlier run would hold deleted temp files.
port=$((8100 + RANDOM % 500))
server_port=$((7800 + RANDOM % 100))
config=$(mktemp --suffix=.yaml)
ledger=$(mktemp --suffix=.db)
printf 'receivers:\n  httpproxy:\n    openai: http://127.0.0.1:%s\n' "$port" > "$config"

python3 scripts/fake_llm.py "$port" &
fake=$!
trap 'GASCOIGNE_SERVER_ADDR=127.0.0.1:$server_port "${GASCOIGNE_BIN:-gascoigne}" server stop >/dev/null 2>&1; kill $fake 2>/dev/null; rm -f "$config" "$ledger"' EXIT
sleep 1

export GASCOIGNE_CONFIG=$config GASCOIGNE_LEDGER=$ledger GASCOIGNE_SERVER_ADDR=127.0.0.1:$server_port
export OPENROUTER_API_KEY=fake OPENROUTER_BASE_URL=http://127.0.0.1:$port/v1
unset GASCOIGNE_DEMO_DRY

for demo in langchain langgraph agno google-adk openai-agents crewai llamaindex pydantic-ai; do
  echo "-- python / $demo (proxy)"
  extra=${demo/google-adk/adk}
  (cd demos/python && uv run --extra "$extra" python "$demo/proxy.py" | grep -E "search_logs \||Bypassed")
done
for demo in ai-sdk langchain openai-agents mastra; do
  echo "-- typescript / $demo (proxy)"
  (cd demos/typescript && pnpm -s "$demo:proxy" | grep -E "search_logs:|no new")
done
echo "-- python / langgraph (auto, MCP)"
(cd demos/python && uv run --extra auto-mcp python langgraph/auto.py | grep -E "Saved|Bypassed")
echo "-- java / spring-ai (auto)"
(cd demos/java && java -jar spring-ai/auto/target/demo-spring-ai-auto-0.0.0.jar | grep -E "Saved|No optimization")
echo "-- java / spring-ai (proxy)"
(cd demos/java && java -jar spring-ai/proxy/target/demo-spring-ai-proxy-0.0.0.jar | grep -E "search_logs:|no new")
