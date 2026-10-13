# Commit style

Same as `gascoigne-cli`, so both repos read alike.

## Subject
`<type>(<scope>): <what changed, no full stop>`, at most 72 characters. The description starts lower
case unless it opens with a name or identifier (`Spring`, `UseGascoigne`).

- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `release`.
- Scope is the area touched, short and lower case: a language (`python`, `typescript`, `go`, `java`,
  `dotnet`, `rust`), a part (`spec`, `demos`, `harness`, `ci`) or a framework (`spring-ai`).
  Drop the scope when a change spans everything: `docs: ...`.
- Say what the change does for a reader of the log, not how: `feat(python): auto() decorates MCP
  calls`, not `add auto.py`.
- Releases: `release: python 0.2.0 <headline>`.

## Body
A short paragraph after a blank line, wrapped at 72 characters, that says **why**: the problem, the
behavior before, what changes now. Skip it when the subject says everything. No bullet dumps of files.

## Rules
- One focused change per commit; do not mix a refactor with a feature.
- Behavior changes update docs and tests in the same commit.
- End with the `Co-Authored-By` trailer when an assistant wrote the change.

```text
feat(spring-ai): @EnableGascoigne shortens every tool call

Tool results reached the model in full unless each tool was wrapped by
hand. One annotation now wraps ToolCallingManager, so @Tool methods,
function callbacks and MCP tools are covered. Nothing is decorated
without the annotation.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

`scripts/commit_style.py` checks the subjects of the commits a pull request adds.
