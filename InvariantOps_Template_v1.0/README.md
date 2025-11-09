# InvariantOps Template — Production as a Continuous Proof

This repository encodes a self-enforcing operational philosophy:
**Invariants → Proof-Gates → Rehearsals → Deployment → Validation → Learning**.

Use it to bootstrap any service (API, data pipeline, microservice) with:
- `OPERATIONAL_INVARIANTS.yml` — the **constitution** of production.
- `.github/workflows/proof-gates.yml` — CI **enforcement** of those laws.
- `docs/operations/runbooks/` — **rehearsed resilience**.
- `k8s/chaos/` — **adversarial testing**.
- `docs/operations/Incident_Retrospective_Template.md` — the **judiciary** (learning loop).

## Quick start
1. Commit this template to your repo root.
2. Adjust thresholds in `audit/OPERATIONAL_INVARIANTS.yml`.
3. Enable GitHub Actions and container registry for image scanning.
4. Run pre-canary script: `scripts/pre_canary.ps1` (or adapt to Bash).
5. Ship with a **canary** and watch SLOs. Rollback on invariant breach.

## Philosophy
> *Production is not a place; it's a set of invariants you can defend.*

## Template Contents

### Core Files
- `audit/OPERATIONAL_INVARIANTS.yml` - Service contract defining all invariants
- `.github/workflows/proof-gates.yml` - CI enforcement of invariants
- `scripts/pre_canary.ps1` - Pre-deployment evidence collection
- `scripts/assert_go_nogo.sh` - GO/NO-GO decision validator

### Runbooks
- `docs/operations/runbooks/WEEK2_LoadSpike.md` - 10× traffic surge response
- `docs/operations/Incident_Retrospective_Template.md` - Post-incident analysis
- `docs/operations/Capacity_Planning_Policy.md` - Quarterly capacity review
- `docs/operations/Error_Budget_Policy.md` - SLO budget management
- `docs/operations/Checklists/Midnight_Page.md` - On-call decision checklist

### Kubernetes
- `k8s/chaos/pod-kill-canary.yaml` - Chaos Mesh pod failure test
- `k8s/canary/flagger-canary.yaml` - Example Flagger canary configuration

### Tests
- `tests/test_auth_conformance.py` - Authentication requirement validation
- `tests/test_invariants.py` - Runtime invariant verification

## Customization

### Step 1: Update OPERATIONAL_INVARIANTS.yml
Edit thresholds for your service:
```yaml
invariants:
  security:
    pip_audit_criticals: "==0"  # Adjust if needed
  quality:
    coverage_total: ">=0.70"     # Raise to 0.80 or 0.90
  performance:
    p95_ms: "<=2500"              # Adjust for your SLO
```

### Step 2: Configure CI/CD
- Set `CRITICAL_PATHS` environment variable to your core modules
- Enable GitHub Actions secrets for image registry access
- Configure Trivy scanner for container images

### Step 3: Adapt Scripts
- Convert `pre_canary.ps1` to Bash if not using Windows
- Update paths to match your project structure
- Add service-specific checks to `assert_go_nogo.sh`

### Step 4: Deploy Monitoring
- Apply Prometheus ServiceMonitor
- Import Grafana dashboards
- Configure alert routing (Slack, PagerDuty)

### Step 5: Test Chaos
- Install Chaos Mesh: `kubectl apply -f https://mirrors.chaos-mesh.org/latest/crd.yaml`
- Validate runbooks by triggering chaos experiments
- Document findings in incident retrospectives

## Integration with ASTRA Core

This template was extracted from the ASTRA Core production deployment process. 
For a complete implementation example, see:
- `audit/GO_LIVE_EVIDENCE_2025-11-01/` - Full evidence pack
- `scripts/pre_canary.ps1` - Production-tested automation
- `k8s/policies/admin-protect.yaml` - Security hardening

## License

MIT License - See LICENSE file for details.

## Support

For questions or contributions:
- Open an issue describing your use case
- Submit PRs with improvements or additional runbooks
- Share your invariant definitions for community benefit

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-01  
**Maintained By**: SRE Community
