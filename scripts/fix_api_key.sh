#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  ASTRA v1.0.0 - QUICK API KEY FIX (Linux/macOS)
# ═══════════════════════════════════════════════════════════════
#
#  Run this once to fix the API key placeholder in .env
#  Safe to run multiple times - will not duplicate keys
#
#  Usage from repo root:
#    bash scripts/fix_api_key.sh
#
# ═══════════════════════════════════════════════════════════════

set -e

echo ""
echo "🔐 Fixing ASTRA_API_KEYS in .env..."

# Generate secure API key
echo "  🔑 Generating secure API key..."
KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

if [ -z "$KEY" ]; then
    echo "  ❌ Failed to generate API key"
    echo "     Ensure Python 3 is available"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "  ⚠️  .env not found, creating..."
    touch .env
fi

# Replace existing key or append if missing
if grep -q '^ASTRA_API_KEYS=' .env; then
    echo "  ℹ️  Existing key found, replacing..."
    # Create backup
    cp .env .env.bak
    # Replace line
    sed -i.tmp "s|^ASTRA_API_KEYS=.*|ASTRA_API_KEYS=$KEY|" .env
    rm -f .env.tmp
else
    echo "  ➕ Adding ASTRA_API_KEYS to .env..."
    echo "ASTRA_API_KEYS=$KEY" >> .env
fi

echo ""
echo "✅ API key configured successfully!"
echo "   Key: ${KEY:0:12}...***"
echo "   Location: .env"
echo ""
echo "🚀 Next step: Run deployment"
echo "   ./scripts/ship.ps1  # or your platform equivalent"
echo ""
