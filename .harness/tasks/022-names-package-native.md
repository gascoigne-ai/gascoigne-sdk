status: todo
kind: chore
commit: refactor(scripts): full parameter names in package_native
scope: scripts/package_native.py

# Full parameter names in package_native.py

`scripts/package_native.py` has six functions with a one-letter parameter `p` (`bundle`, `python`, `npm`, `java`, `dotnet`, `rust`) and a few `p` loop and comprehension variables over `PLATFORMS`. Rename the parameters to `platform` and, in the same file, the `p` variables that read the same values. Behavior does not change. Task 020 needs this first, because its whole-repo check fails on these names.

Model: unchanged.

## Acceptance
- `python3 scripts/style.py --params scripts/package_native.py` reports nothing.
- `python3 scripts/package_native.py` behaves as before (same arguments, same output files).
- `make check` passes.
