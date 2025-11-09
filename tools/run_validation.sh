#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${1:-"http://localhost:8080"}
LOCUST_USERS=${2:-120}
LOCUST_RATE=${3:-40}
WATCH_MINS=${4:-15}

echo "[*] Starting production validation sequence"

# 1. Run the Python validation suite
echo "[+] Running validation checks..."
python tools/validate_production.py --host "$BASE_URL"

# 2. Start load test in background
echo "[+] Starting load test..."
locust -f tools/locustfile.py --headless -u $LOCUST_USERS -r $LOCUST_RATE -t "${WATCH_MINS}m" -H "$BASE_URL" --csv=prod_validation &
LOCUST_PID=$!

# 3. Watch key metrics for specified duration
echo "[+] Watching metrics for ${WATCH_MINS} minutes..."
for i in $(seq 1 $WATCH_MINS); do
    # Query Prometheus for key metrics
    # Add your prometheus query commands here
    sleep 60
    echo "Minute $i/$WATCH_MINS completed"
done

# 4. Check Locust results
wait $LOCUST_PID
if [ $? -ne 0 ]; then
    echo "[!] Load test failed"
    exit 1
fi

# Parse p95 from Locust CSV
P95=$(awk -F',' '$1=="answer" && $2=="95%" {print $3}' prod_validation_requests.csv)
if (( $(echo "$P95 > 2500" | bc -l) )); then
    echo "[!] P95 latency exceeded threshold: ${P95}ms"
    exit 1
fi

echo "[+] Validation complete - system ready for promotion"