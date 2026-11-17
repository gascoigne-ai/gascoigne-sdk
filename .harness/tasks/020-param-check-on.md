status: todo
kind: chore
commit: build: mise check rejects one-letter parameters
scope: mise.toml, scripts/style.py
depends_on: 014-names-python, 015-names-typescript, 016-names-go, 017-names-rust, 018-names-java, 019-names-dotnet

# Parameter check in mise check

Add the parameter check to the default `style` run over the whole repo.

Model: unchanged.

## Acceptance
- A one-letter parameter added on purpose fails the check, then is reverted.
- `mise run check` passes.
