# Entry points over mise. `make check` runs every check in a sandboxed HOME so a
# test can never touch the real gascoigne config; the toolchains and caches stay
# shared with the real HOME, so nothing is downloaded again.

REAL_HOME := $(HOME)

# A system dotnet host without an SDK can sit before mise's dotnet in PATH; the
# PATH line in `check` puts the mise one first.

.PHONY: check e2e demo style

check:
	@sandbox=$$(mktemp -d) && trap 'rm -rf "$$sandbox"' EXIT && \
	HOME="$$sandbox" \
	XDG_CONFIG_HOME="$$sandbox/config" \
	XDG_STATE_HOME="$$sandbox/state" \
	XDG_DATA_HOME="$(REAL_HOME)/.local/share" \
	XDG_CACHE_HOME="$(REAL_HOME)/.cache" \
	MISE_CONFIG_DIR="$(REAL_HOME)/.config/mise" \
	MISE_DATA_DIR="$(REAL_HOME)/.local/share/mise" \
	MISE_CACHE_DIR="$(REAL_HOME)/.cache/mise" \
	CARGO_HOME="$(REAL_HOME)/.cargo" \
	RUSTUP_HOME="$(REAL_HOME)/.rustup" \
	GOPATH="$(REAL_HOME)/.go" \
	GOCACHE="$(REAL_HOME)/.cache/go-build" \
	UV_CACHE_DIR="$(REAL_HOME)/.cache/uv" \
	PATH="$(REAL_HOME)/.local/share/mise/dotnet-root:$$PATH" \
	mise run check

e2e:
	mise run e2e

demo:
	mise run demo

style:
	mise run style
