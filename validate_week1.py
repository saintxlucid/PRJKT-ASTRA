"""Week-1 Hardening Validation Check"""
import os
import json

checks = [
    ("security/", "Security directory"),
    ("security/models_registry.yaml", "Model registry"),
    ("security/verify_models.py", "Model verification script"),
    ("core/memory_signing.py", "Memory signing module"),
    ("tools/backup/", "Backup tools directory"),
    ("tools/backup/backup_runner.py", "Backup runner"),
    ("tools/backup/restore_runner.py", "Restore runner"),
    ("tools/security/", "Security tools directory"),
    ("tools/security/run_scans.ps1", "Security scan runner"),
    ("data/backups/", "Backups storage directory"),
    ("audit/bandit_report.json", "Bandit security report"),
    ("archive/k8s_for_scale/", "Archived K8s manifests"),
    ("docker-compose.yml", "Docker Compose config"),
    ("WEEK_1_HARDENING_RUNBOOK.md", "Week-1 runbook"),
]

print("🛡️ Week-1 Hardening Validation\n" + "=" * 50)

passed = 0
failed = 0

for path, desc in checks:
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {desc:30s} {path}")
    if exists:
        passed += 1
    else:
        failed += 1

print("=" * 50)
print(f"✅ Passed: {passed}/{len(checks)}")
if failed > 0:
    print(f"❌ Failed: {failed}/{len(checks)}")

result = {
    "week1_validation": {
        "passed": passed,
        "failed": failed,
        "total": len(checks),
        "status": "PASS" if failed == 0 else "PARTIAL"
    }
}

print("\n" + json.dumps(result, indent=2))
exit(0 if failed == 0 else 1)
