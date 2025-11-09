#!/bin/bash

# ============================================================
# ASTRA CORE LAUNCH SCRIPT (Linux/macOS) - GPT-OSS edition
# ============================================================

echo -e "\033[36m🔹 Initializing ASTRA Core...\033[0m"
cd "$(dirname "$0")/.."

# 1️⃣  Activate Python environment
if [ ! -d "./.venv" ]; then
    echo -e "\033[36m🪶 Creating virtual environment...\033[0m"
    python3 -m venv .venv
fi

source ./.venv/bin/activate

# 2️⃣  Ensure dependencies
echo -e "\033[36m📦 Installing/updating dependencies...\033[0m"
pip install --upgrade pip wheel poetry > /dev/null 2>&1
poetry install --no-root > /dev/null 2>&1

# 3️⃣  Verify GPT-OSS model
echo -e "\033[36m🔍 Checking GPT-OSS-20B model...\033[0m"
VERIFY_OUTPUT=$(python3 ./scripts/verify_model.py)
VERIFY_STATUS=$(echo $VERIFY_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

if [ "$VERIFY_STATUS" != "ok" ]; then
    echo -e "\033[31m❌ Model missing or corrupted. Please place gpt-oss-20b-q4_k_m.gguf in /models.\033[0m"
    exit 1
fi

VERIFY_SIZE=$(echo $VERIFY_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['size_gb'])")
VERIFY_SHA=$(echo $VERIFY_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['sha'])")
echo -e "\033[32m✅ Model verified: ${VERIFY_SIZE} GB, SHA ${VERIFY_SHA}\033[0m"

# 4️⃣  Hardware detection
echo -e "\033[36m🧠 Detecting hardware...\033[0m"
HW_OUTPUT=$(python3 ./scripts/hw_detect.py)
HW_OS=$(echo $HW_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['os'])")
HW_RAM=$(echo $HW_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['ram_gb'])")
HW_GPU=$(echo $HW_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['gpu'])")
HW_GPU_NAME=$(echo $HW_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['gpu_name'])")
HW_VRAM=$(echo $HW_OUTPUT | python3 -c "import sys, json; print(json.load(sys.stdin)['vram_gb'])")

echo -e "\033[36m→ ${HW_OS}, ${HW_RAM} GB RAM, GPU=${HW_GPU_NAME} (${HW_VRAM} GB VRAM)\033[0m"

# Set runtime optimization vars
if [ "$HW_GPU" = "True" ]; then
    export ASTRA_MODE="GPU"
    export ASTRA_BATCH="8"
    echo -e "\033[36m⚡ GPU mode enabled with batch size 8\033[0m"
else
    export ASTRA_MODE="CPU"
    export ASTRA_BATCH="2"
    echo -e "\033[36m💻 CPU mode enabled with batch size 2\033[0m"
fi

# 5️⃣  Launch core API
echo -e "\033[36m🚀 Starting ASTRA Core API...\033[0m"
nohup uvicorn astra.api.app:app --host 0.0.0.0 --port 8080 > /dev/null 2>&1 &

# 6️⃣  Start watchdog
echo -e "\033[36m🛡️  Starting self-healing watchdog...\033[0m"
nohup python3 ./scripts/selfheal.py > /dev/null 2>&1 &

# 7️⃣  Health check loop
echo -e "\033[36m🧩 Verifying startup...\033[0m"
for i in {1..10}; do
    sleep 3
    if curl -s -f -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/v1/system/health | grep -q "200"; then
        echo -e "\033[32m✅ ASTRA Core is online.\033[0m"
        break
    fi
    
    if [ $i -eq 10 ]; then
        echo -e "\033[31m⚠️ ASTRA failed to start properly.\033[0m"
        exit 1
    fi
done

echo -e "\033[36m✨ Ready for further development — GPT-OSS core active.\033[0m"
echo -e "\033[33m🔄 Watchdog is monitoring API health in the background.\033[0m"
echo -e "\033[34m🔗 API available at http://127.0.0.1:8080\033[0m"