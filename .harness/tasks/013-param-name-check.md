status: todo
kind: feature
commit: build: style.py reports one-letter parameters
scope: scripts/style.py, scripts/test_style.py

# style.py --params

Add `python3 scripts/style.py --params <paths>`: Python via `ast`, TypeScript, Go, Rust, Java and C# via regex over signatures and lambda or closure parameters. Exempt `t`/`b` of test types, `_`, type parameters and Go receivers. Not part of the check yet.

## Model
A violation is (file, line, name, language). No persistence.

## Acceptance
- Test first: the tests that state the behavior, run and seen failing for the expected reason. Table with a bad and an allowed snippet per language.
- `mise run check` passes.
