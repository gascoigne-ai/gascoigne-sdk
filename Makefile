# Entry points over mise. The checks run in a sandboxed HOME so a test can never
# touch the real gascoigne config; the toolchains and caches stay shared with the
# real HOME, so nothing is downloaded again.

REAL_HOME := $(HOME)

# One check language per SDK; `make check-<lang>` runs mise task `<lang>:check`.
LANGS := py ts go native java dotnet rust

# A system dotnet host without an SDK can sit before mise's dotnet in PATH; the
# PATH line in `sandboxed` puts the mise one first.
# Usage: $(call sandboxed,<mise task>)
define sandboxed
sandbox=$$(mktemp -d) && trap 'rm -rf "$$sandbox"' EXIT && \
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
mise run $(1)
endef

.PHONY: check e2e demo demo-proxy style native-build $(LANGS:%=check-%)

check:
	@$(call sandboxed,check)

$(LANGS:%=check-%): check-%:
	@$(call sandboxed,$*:check)

native-build:
	mise run native:build

e2e:
	mise run e2e

demo:
	mise run demo

demo-proxy:
	mise run demo:proxy

style:
	mise run style
