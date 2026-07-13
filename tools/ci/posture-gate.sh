#!/usr/bin/env bash
# Local/CI wrapper for the composite GitHub Action posture gate script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "${ROOT}/.github/actions/posture-gate/posture-gate.sh" "$@"
