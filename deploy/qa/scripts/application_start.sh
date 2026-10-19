#!/usr/bin/env bash
set -euo pipefail
cp -f /opt/qcg-mcp/release/docker-compose-qa.yml /opt/qcg-mcp/release/qa.env /opt/qcg-mcp/
cd /opt/qcg-mcp
docker compose -f docker-compose-qa.yml up -d
echo "container started"
