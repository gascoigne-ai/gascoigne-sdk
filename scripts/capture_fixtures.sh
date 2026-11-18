#!/usr/bin/env bash
# Capture real /sdk/v1 responses from a gascoigne server into spec/fixtures/.
# Usage: scripts/capture_fixtures.sh [path-to-gascoigne-binary]
# Without an argument the binary is built from the `cli/` submodule into a temp dir.
# HOME and XDG_* point at a temp dir so the real config and ledger are never touched.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/spec/fixtures"
tmp="$(mktemp -d)"
server_pid=""
cleanup() {
  [[ -n "$server_pid" ]] && kill "$server_pid" 2>/dev/null || true
  rm -rf "$tmp"
}
trap cleanup EXIT

bin="${1:-}"
if [[ -z "$bin" ]]; then
  bin="$tmp/gascoigne"
  (cd "$root/cli" && env -u GOFLAGS go build -o "$bin" ./cmd/gascoigne)
fi

export HOME="$tmp/home"
export XDG_CONFIG_HOME="$tmp/config"
export XDG_CACHE_HOME="$tmp/cache"
export XDG_DATA_HOME="$tmp/data"
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"

# A free port: bind port 0, read it back, release it.
port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
export GASCOIGNE_SERVER_ADDR="127.0.0.1:$port"
base="http://$GASCOIGNE_SERVER_ADDR/sdk/v1"

"$bin" server run -addr "$GASCOIGNE_SERVER_ADDR" >"$tmp/server.log" 2>&1 &
server_pid=$!
for _ in $(seq 1 50); do
  curl -fs "$base/health" >/dev/null 2>&1 && break
  sleep 0.1
done

mkdir -p "$out"
rm -f "$out"/*.json "$out"/*.txt

curl -fs "$base/health" | python3 -m json.tool >"$out/health.json"

# Large repetitive text the optimizers shrink.
python3 - >"$tmp/big.json" <<'PY'
import json
lines = [f"2026-01-01T00:00:{i % 60:02d}Z INFO worker started job={i % 3} status=ok" for i in range(400)]
print(json.dumps({"text": "\n".join(lines) + "\n", "tool": "bash", "cmd": "tail -n 400 app.log",
                  "session": "fixture-session", "agent": "fixture-agent", "model": "fixture-model"}))
PY
curl -fs -X POST -d @"$tmp/big.json" "$base/optimize" >"$tmp/optimized.raw"
python3 -m json.tool "$tmp/optimized.raw" >"$out/optimize_optimized.json"

curl -fs -X POST -d '{"text":"ok","tool":"bash","cmd":"echo ok"}' "$base/optimize" \
  | python3 -m json.tool >"$out/optimize_skipped.json"

raw_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("raw_id",""))' "$tmp/optimized.raw")"
if [[ -z "$raw_id" ]]; then
  echo "optimized call returned no raw_id" >&2
  exit 1
fi
curl -fs "$base/raw/$raw_id" >"$out/raw.txt"

curl -fs "$base/stats" | python3 -m json.tool >"$out/stats.json"
curl -fs "$base/recent" | python3 -m json.tool >"$out/recent.json"

if grep -rq /home "$out"; then
  echo "fixtures contain a home path" >&2
  exit 1
fi
echo "fixtures written to spec/fixtures"
