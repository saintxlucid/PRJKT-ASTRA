#!/usr/bin/env bash
set -euo pipefail
STACK=${1:-"astra"}
SERVICE=${2:-"astra-core"}
PREV_TAG=${3:-"vPrev"}

echo "[*] Draining..."
curl -fsS -X POST http://localhost:8080/admin/drain || true
sleep 5

echo "[*] Rolling back $SERVICE to $PREV_TAG"
IMAGE=$(docker compose ps --format json | jq -r ".[] | select(.Service==\"$SERVICE\") | .Image" | head -n1)
BASE=${IMAGE%:*}
docker compose up -d --no-deps --scale "$SERVICE"=0
docker compose pull "$SERVICE"
IMAGE_PIN="$BASE:$PREV_TAG" docker compose up -d "$SERVICE"

echo "[*] Waiting for readiness..."
for i in {1..30}; do
  sleep 2
  READY=$(curl -fsS http://localhost:8080/ready | jq -r .ready || echo "false")
  [[ "$READY" == "true" ]] && { echo "[+] Ready"; exit 0; }
done
echo "[!] Rollback started but readiness not confirmed"; exit 1