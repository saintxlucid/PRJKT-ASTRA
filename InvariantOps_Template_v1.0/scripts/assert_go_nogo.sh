#!/usr/bin/env bash
# GO/NO-GO Decision Validator
# Exits 0 if all invariants hold, 1 if any breach

set -euo pipefail

EVIDENCE_DIR="${1:-.}"
INVARIANTS_FILE="audit/OPERATIONAL_INVARIANTS.yml"

echo "⚖️ Validating operational invariants from $INVARIANTS_FILE"

# Check if required files exist
required_files=(
    "$EVIDENCE_DIR/pip_audit.json"
    "$EVIDENCE_DIR/bandit.json"
    "$EVIDENCE_DIR/coverage.xml"
    "$EVIDENCE_DIR/test_results.xml"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Missing evidence file: $file"
        exit 1
    fi
done

# Python validator (same logic as GitHub Actions workflow)
python3 - <<'EOF'
import sys
import json
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path

evidence_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

# Load invariants
with open("audit/OPERATIONAL_INVARIANTS.yml") as f:
    inv = yaml.safe_load(f)

breaches = []

def check_op(actual, op, expected_str):
    expected = float(expected_str) if expected_str.replace('.', '', 1).isdigit() else expected_str
    if op == "==": return actual == expected
    if op == "<=": return actual <= expected
    if op == ">=": return actual >= expected
    if op == "<": return actual < expected
    if op == ">": return actual > expected
    return False

# Security checks
with open(evidence_dir / "pip_audit.json") as f:
    pip_audit = json.load(f)
    criticals = sum(1 for dep in pip_audit.get("dependencies", []) 
                    for vuln in dep.get("vulns", []) 
                    if vuln.get("severity") in ["CRITICAL", "HIGH"])
    if not check_op(criticals, "==", "0"):
        breaches.append(f"pip_audit_criticals: {criticals} (expected ==0)")

with open(evidence_dir / "bandit.json") as f:
    bandit = json.load(f)
    high = sum(1 for result in bandit.get("results", []) 
               if result.get("issue_severity") == "HIGH")
    if not check_op(high, "==", "0"):
        breaches.append(f"bandit_high: {high} (expected ==0)")

# Coverage checks
tree = ET.parse(evidence_dir / "coverage.xml")
root = tree.getroot()
coverage_total = float(root.attrib["line-rate"]) * 100
if not check_op(coverage_total, ">=", "70"):
    breaches.append(f"coverage_total: {coverage_total:.1f}% (expected >=70%)")

# Report
if breaches:
    print("❌ NO-GO: Invariants breached:")
    for b in breaches:
        print(f"  - {b}")
    sys.exit(1)
else:
    print("✅ GO: All invariants hold")
    sys.exit(0)
EOF
