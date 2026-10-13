#!/usr/bin/env bash
# Runs every wrapping demo in dry mode (the agent is built, the LLM is not called).
# Layout: demos/<language>/<framework>/<mode>, with mode = wrap | proxy | auto.
set -euo pipefail
cd "$(dirname "$0")/.."
export GASCOIGNE_DEMO_DRY=1

for demo in langchain langgraph agno google-adk openai-agents crewai llamaindex pydantic-ai smolagents; do
  echo "-- python / $demo"
  extra=${demo/google-adk/adk}
  (cd demos/python && uv run --extra "$extra" python "$demo/wrap.py" | tail -2)
done
for demo in ai-sdk langchain openai-agents mastra; do
  echo "-- typescript / $demo"
  (cd demos/typescript && pnpm -s "$demo:wrap" | tail -2)
done
echo "-- java / spring-ai"
(cd demos/java && java -jar spring-ai/wrap/target/demo-spring-ai-wrap-0.0.0.jar | tail -2)
echo "-- java / langchain4j"
(cd demos/java && mvn -q -B -pl langchain4j/wrap exec:java | tail -2)
echo "-- go / langchaingo"
(cd demos/go && go run ./langchaingo/wrap | tail -2)
echo "-- rust / plain"
(cd rust && cargo run -q --example plain | tail -2)
