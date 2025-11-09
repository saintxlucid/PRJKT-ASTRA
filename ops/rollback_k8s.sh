#!/usr/bin/env bash
set -euo pipefail
NS=${1:-"astra"}
DEPLOY=${2:-"astra-core"}

echo "[*] Draining..."
kubectl -n $NS exec deploy/$DEPLOY -- curl -s -X POST localhost:8080/admin/drain || true
sleep 5
echo "[*] kubectl rollout undo"
kubectl -n $NS rollout undo deploy/$DEPLOY
kubectl -n $NS rollout status deploy/$DEPLOY --timeout=120s
kubectl -n $NS get po -l app=$DEPLOY -w