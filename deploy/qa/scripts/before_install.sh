#!/usr/bin/env bash
# Clear the previous staged release; the running container keeps serving until application_start.sh swaps it.
set -euo pipefail
rm -rf /opt/qcg-mcp/release
mkdir -p /opt/qcg-mcp/release
