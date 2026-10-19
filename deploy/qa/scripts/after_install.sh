#!/usr/bin/env bash
# Load the image the runner built, and remember what's live so validate_service.sh can roll back to it.
set -euo pipefail
cd /opt/qcg-mcp/release
SHA="$(cat COMMIT_SHA 2>/dev/null || echo unknown)"
docker inspect --format '{{.Image}}' qcg-mcp-qa 2>/dev/null > /opt/qcg-mcp/.previous_image || true
gunzip -c image.tar.gz | docker load
rm -f image.tar.gz
docker tag "qcg-mcp:${SHA}" qcg-mcp:latest
echo "image loaded: qcg-mcp:${SHA}"
