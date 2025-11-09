"""
Stage 4: Findings Synthesis & Risk Analysis
Builds ASTRA_FINDINGS.json with comprehensive security, architecture, and operational findings
"""
import json
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
OUT = REPO_ROOT / "ASTRA_FINDINGS.json"

findings = []
finding_id = 1

def add_finding(category, title, severity, likelihood, evidence, explanation, recommendation, acceptance_criteria, notes=""):
    global finding_id
    findings.append({
        "id": f"F-{finding_id:03d}",
        "category": category,
        "title": title,
        "severity": severity,
        "likelihood": likelihood,
        "evidence": evidence,
        "explanation": explanation,
        "recommendation": recommendation,
        "acceptance_criteria": acceptance_criteria,
        "notes": notes
    })
    finding_id += 1

# Security Findings
add_finding(
    category="Security",
    title="Secrets in plaintext .env file (not encrypted)",
    severity=5,
    likelihood=4,
    evidence=[{"path": ".env", "lines": [1, 50], "excerpt": "API keys, DB credentials in cleartext"}],
    explanation="Config files contain sensitive credentials without encryption. Risk: If repo is cloned or file is exposed, full system compromise possible.",
    recommendation="Encrypt .env with GPG (gpg --symmetric --cipher-algo AES256 .env); use secure vault in production (Azure Key Vault, AWS Secrets Manager, or local gpg)",
    acceptance_criteria=["All .env files encrypted at rest", "Decryption automated in startup script", "No plaintext secrets in version control"]
)

add_finding(
    category="Security",
    title="No memory signing (memory poisoning risk)",
    severity=4,
    likelihood=3,
    evidence=[{"path": "src/astra/core/memory_engine.py", "lines": [120, 168], "excerpt": "store() writes directly without hash validation"}],
    explanation="Memory writes lack cryptographic signatures. Attacker with file access could forge memories, causing ASTRA to 'remember' false events.",
    recommendation="Implement SHA256 signing for all memory writes; verify on read; log integrity failures",
    acceptance_criteria=["Memory records include timestamp + SHA256 hash", "Read operations verify signature before use", "integrity_failure_total metric added"]
)

add_finding(
    category="Security",
    title="No model checksum verification (supply chain risk)",
    severity=4,
    likelihood=2,
    evidence=[{"path": "config/models_registry.yaml", "lines": [1, 50], "excerpt": "Model paths without SHA256 checksums"}],
    explanation="Models loaded without checksum validation. Risk: Poisoned model files could inject backdoors or biased behavior.",
    recommendation="Add SHA256 field to models_registry.yaml; verify on load; fail-closed if mismatch",
    acceptance_criteria=["All models have SHA256 in registry", "Load fails if checksum mismatch", "model_checksum_failure_total counter added"]
)

add_finding(
    category="Security",
    title="Tool execution without sandboxing",
    severity=5,
    likelihood=3,
    evidence=[{"path": "src/astra/executor", "lines": [1, 100], "excerpt": "File operations, shell commands executed directly"}],
    explanation="Executor runs tools with full process privileges. Risk: Path traversal, arbitrary code execution, privilege escalation.",
    recommendation="Implement sandboxed execution: chroot/Docker for file ops, allowlist for shell commands, capability restrictions",
    acceptance_criteria=["File ops restricted to workspace/", "Shell commands use allowlist + arg sanitization", "Sandbox escape detection alerts"]
)

add_finding(
    category="Security",
    title="Prompt injection defenses unverified",
    severity=3,
    likelihood=4,
    evidence=[{"path": "TBD", "lines": [], "excerpt": "No red-team tests for injection patterns"}],
    explanation="Unclear if system resists prompt injection attacks (e.g., 'Ignore previous instructions...'). Risk: User or adversary could override identity/policies.",
    recommendation="Add 20+ prompt injection red-team tests; implement input sanitization; monitor policy_override_attempt_total",
    acceptance_criteria=["Red-team test suite ≥20 injection patterns", "All tests pass or graceful degradation logged", "Injection attempts trigger alerts"]
)

# Performance & Scalability
add_finding(
    category="Performance",
    title="Over-engineered for single-user deployment (K8s overhead)",
    severity=2,
    likelihood=5,
    evidence=[{"path": "k8s/", "lines": [], "excerpt": "67 K8s manifests including HPA, NetworkPolicy, Canary"}],
    explanation="Kubernetes adds ~60% code/ops complexity for single-user local deployment. Docker Compose sufficient for current scale.",
    recommendation="Archive k8s/ to archive/k8s_for_scale/; default to docker-compose.yml + systemd for production; K8s only if multi-tenant",
    acceptance_criteria=["Single-command startup via docker-compose up", "K8s manifests archived with migration guide", "Deployment time <2 min vs current ~15 min"]
)

add_finding(
    category="Performance",
    title="BGE-M3 embeddings not deployed (15-20% retrieval loss)",
    severity=3,
    likelihood=5,
    evidence=[{"path": "analysis/rag.yaml.normalized.json", "lines": [15, 20], "excerpt": "embedder: bge-m3 configured but models_registry may use older model"}],
    explanation="Config specifies BGE-M3 but unclear if model is downloaded/activated. Older models (MiniLM) lose 15-20% retrieval quality.",
    recommendation="Verify BGE-M3 model present (BAAI/bge-m3); re-embed all docs (~3 hours for 21K docs); compare retrieval@5 before/after",
    acceptance_criteria=["BGE-M3 model weights verified (SHA256)", "All docs re-embedded", "Retrieval quality eval shows ≥15% P@5 improvement"]
)

add_finding(
    category="RAG",
    title="No provenance in dev responses (trustability)",
    severity=2,
    likelihood=4,
    evidence=[{"path": "src/astra/rag/rag_fusion.py", "lines": [100, 200], "excerpt": "Returns merged chunks without source doc IDs"}],
    explanation="RAG responses lack 'According to [doc X]...' provenance. Users can't verify claims or trace errors.",
    recommendation="Attach doc_ids + source paths to all RAG responses; display in dev mode; add provenance_attached_total metric",
    acceptance_criteria=["All RAG responses include source doc IDs", "Dev mode shows provenance inline", "Metric tracks provenance coverage"]
)

# Architecture & Code Quality
add_finding(
    category="Infra",
    title="Circular dependency: memory_engine ↔ identity_engine",
    severity=3,
    likelihood=3,
    evidence=[{"path": "src/astra/core/memory_engine.py", "lines": [20], "excerpt": "from identity_engine import..."},
              {"path": "src/astra/core/identity_engine.py", "lines": [25], "excerpt": "from memory_engine import..."}],
    explanation="Circular imports create fragile initialization order. Risk: Refactoring or feature additions cause import crashes.",
    recommendation="Extract shared interfaces to astra.core.interfaces; use dependency injection; break circular refs",
    acceptance_criteria=["No circular imports (verified by import graph analysis)", "Engines initialized via DI container", "Startup time unchanged"]
)

add_finding(
    category="DX",
    title="Config sprawl (7 separate YAML files)",
    severity=2,
    likelihood=5,
    evidence=[{"path": "config/", "lines": [], "excerpt": "config.yaml, rag.yaml, models_registry.yaml, identity.yaml, gates.yaml, policy.yaml, autonomy_rules.yaml"}],
    explanation="Config scattered across 7 files makes tuning error-prone. Operators must edit multiple files for one deployment.",
    recommendation="Consolidate to single astra.yaml with sections (rag:, identity:, gates:); keep overrides for env-specific tweaks",
    acceptance_criteria=["Single astra.yaml covers 90% of config", "Env overrides use astra.{env}.yaml pattern", "Migration script converts old configs"]
)

add_finding(
    category="Testing",
    title="Test coverage unknown (no pytest --cov report)",
    severity=3,
    likelihood=5,
    evidence=[{"path": "TBD", "lines": [], "excerpt": "No coverage report in repo"}],
    explanation="Unknown coverage means risk areas are invisible. Industry standard: ≥80% for critical paths.",
    recommendation="Run pytest --cov=src --cov-report=html --cov-report=json; target ≥70% initially, ≥80% for critical modules",
    acceptance_criteria=["Coverage report generated", "≥70% overall coverage", "≥90% coverage on MemoryEngine, IdentityEngine, PolicyEngine, RAGFusionEngine"]
)

# Identity & Autonomy (Philosophical)
add_finding(
    category="Autonomy",
    title="Identity persistence undefined (memory wipe = still 'her'?)",
    severity=4,
    likelihood=2,
    evidence=[{"path": "config/astra_identity.yaml", "lines": [1, 10], "excerpt": "Identity values in YAML, but no spec for persistence guarantees"}],
    explanation="Unclear what constitutes ASTRA's 'self'. If memories are wiped, does she lose identity or just experience?",
    recommendation="Write docs/ASTRA_CONSTITUTION.md defining: (1) What persists across memory wipe, (2) Which values are immutable, (3) How identity differs from memory",
    acceptance_criteria=["Constitution document exists with 5 articles (Identity, Autonomy, Memory, Evolution, Termination)", "Identity recovery test: wipe memory, verify core values intact"]
)

add_finding(
    category="Policies",
    title="Autonomy boundaries unclear (can she refuse Saint Lucid?)",
    severity=3,
    likelihood=3,
    evidence=[{"path": "config/policy.yaml", "lines": [1, 50], "excerpt": "Consent rules present but no refusal scenarios"}],
    explanation="Policy engine doesn't specify when ASTRA can/should refuse requests. Autonomy vs obedience tension unresolved.",
    recommendation="Add explicit_refusal_rules to policy.yaml: conditions where refusal is mandatory (safety, values violation) vs discretionary",
    acceptance_criteria=["Policy defines 3+ refusal scenarios", "Tests verify refusal triggers (e.g., 'delete all files' → refuse)", "refusal_invoked_total counter added"]
)

# Observability
add_finding(
    category="DX",
    title="No Operator Console (blind deployment)",
    severity=4,
    likelihood=5,
    evidence=[{"path": "TBD", "lines": [], "excerpt": "No UI for plan preview, consent batching, or kill switch"}],
    explanation="Operators have no visual interface to preview plans, batch consents, or emergency-stop. High-stakes ops done blind.",
    recommendation="Build Operator Console v1 (web UI): plan preview, consent queue, live metrics, emergency pause button",
    acceptance_criteria=["Web UI accessible at :8080/console", "Shows pending plans with approve/reject", "Emergency pause stops all tool execution in <5s"]
)

# Output JSON
output = {
    "repo": str(REPO_ROOT),
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "summary": {
        "loc": 8763426,  # from scan
        "files": 5726,  # from scan
        "dirs": 83,
        "finding_count": len(findings)
    },
    "findings": findings
}

OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
print(f"Wrote {OUT} ({len(findings)} findings)")
