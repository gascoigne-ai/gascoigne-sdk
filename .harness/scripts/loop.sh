#!/usr/bin/env bash
# Runs the shared task loop with this repo's verification.
exec env VERIFY_CMD="${VERIFY_CMD:-mise run check}" "$(dirname "$0")/../common/scripts/loop.sh" "$@"
