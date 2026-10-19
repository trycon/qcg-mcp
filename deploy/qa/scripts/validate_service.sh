#!/usr/bin/env bash
# Fail the deployment unless the new container answers /health, and put the previous image back.
set -euo pipefail
for i in $(seq 1 24); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:3030/health || echo 000)" = "200" ]; then
    echo "healthy after $((i * 5))s"
    # The box runs about 85% full: keep the two newest builds (newest first), drop the rest.
    docker images qcg-mcp --format '{{.Tag}}' | grep -v '^latest$' | tail -n +3 | xargs -r -I{} docker rmi "qcg-mcp:{}" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 5
done
echo "unhealthy after 120s, rolling back"
PREV="$(cat /opt/qcg-mcp/.previous_image 2>/dev/null || true)"
if [ -n "$PREV" ]; then
  docker tag "$PREV" qcg-mcp:latest
  (cd /opt/qcg-mcp && docker compose -f docker-compose-qa.yml up -d)
  echo "rolled back to $PREV"
fi
exit 1
