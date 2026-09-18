#!/usr/bin/env bash
# ==============================================================================
# Placement Copilot - Model Service Contract Smoke Test
# ==============================================================================
# Delegate execution to model-service/smoke_test.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/model-service/smoke_test.sh" "$@"
