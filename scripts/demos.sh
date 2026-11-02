#!/usr/bin/env bash
# Runs every wrapping demo in dry mode (the agent is built, the LLM is not called).
# Layout: demos/<language>/<framework>/<mode>, with mode = wrap | proxy | auto | native.
set -euo pipefail
cd "$(dirname "$0")/.."
export GASCOIGNE_DEMO_DRY=1

for demo in langchain langgraph agno google-adk openai-agents pydantic-ai smolagents; do
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
echo "-- dotnet / microsoft-extensions-ai"
(cd demos/dotnet && dotnet run --project microsoft-extensions-ai/wrap | tail -2)
echo "-- go / langchaingo"
(cd demos/go && go run ./langchaingo/wrap | tail -2)
echo "-- rust / plain"
(cd demos/rust/plain && cargo run -q | tail -2)

# Native mode: the engine runs in the demo's own process, no server. Needs libgascoigne
# (`mise run native:build`, or GASCOIGNE_LIB).
export GASCOIGNE_LIB="${GASCOIGNE_LIB:-$PWD/native/dist/libgascoigne.so}"
if [ -f "$GASCOIGNE_LIB" ]; then
  for demo in langchain langgraph agno google-adk openai-agents pydantic-ai smolagents; do
    echo "-- native / python $demo"
    extra=${demo/google-adk/adk}
    (cd demos/python && uv run --extra "$extra" python "$demo/native.py" | tail -2)
  done
  for demo in ai-sdk langchain openai-agents mastra; do
    echo "-- native / typescript $demo"
    (cd demos/typescript && pnpm -s "$demo:native" | tail -2)
  done
  echo "-- native / java langchain4j"
  (cd demos/java && mvn -q -B -pl langchain4j/native exec:java | tail -2)
  echo "-- native / dotnet microsoft-extensions-ai"
  (cd demos/dotnet && dotnet run --project microsoft-extensions-ai/native | tail -2)
  echo "-- native / java spring-ai"
  (cd demos/java && java -jar spring-ai/native/target/demo-spring-ai-native-0.0.0.jar | tail -2)
  echo "-- native / go plain"
  (cd native && go run ./examples/plain | tail -2)
  echo "-- native / rust plain"
  (cd demos/rust/plain && cargo run -q --bin native | tail -2)
else
  echo "-- native demos skipped: no libgascoigne (mise run native:build)"
fi
