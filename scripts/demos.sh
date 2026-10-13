#!/usr/bin/env bash
# Runs every demo in dry mode (the agent is built, the LLM is not called).
set -euo pipefail
cd "$(dirname "$0")/.."
export GASCOIGNE_DEMO_DRY=1

for demo in langchain langgraph agno google-adk openai-agents crewai llamaindex pydantic-ai smolagents; do
  echo "-- python / $demo"
  extra=${demo/google-adk/adk}
  (cd demos/python && uv run --extra "$extra" python "$demo/main.py" | tail -2)
done
for d in ai-sdk langchain openai-agents mastra; do
  echo "-- typescript / $d"
  (cd typescript/demos && pnpm -s "$d" | tail -2)
done
echo "-- java / spring-ai"
(cd java/demos && java -jar spring-ai/target/demo-spring-ai-0.0.0.jar | tail -2)
echo "-- java / langchain4j"
(cd java/demos && mvn -q -B -pl langchain4j exec:java | tail -2)
echo "-- go / langchaingo"; (cd go/demos && go run ./langchaingo | tail -2)
echo "-- rust"; (cd rust && cargo run -q --example logs | tail -2)
