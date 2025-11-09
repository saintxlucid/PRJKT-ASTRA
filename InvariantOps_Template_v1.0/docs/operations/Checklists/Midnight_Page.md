# Midnight Page Checklist

**Context**: You're on-call. It's 03:00. Alert fires. Before you act, ask:

## System Understanding
- [ ] What changed in the last 4 hours? (deployments, config, traffic)
- [ ] Is this alert actionable, or should it be tuned?
- [ ] What's the blast radius? (% of users, requests, services affected)

## Failure Modes
- [ ] Could this change trigger retry storms? Where are retry budgets enforced?
- [ ] What happens at 10× traffic for 15 minutes? (load test data available?)
- [ ] Which circuit breaker trips first, and what does the user see?
- [ ] If vector DB goes read-only for 10 min, how do we degrade?
- [ ] If secrets rotate mid-request, do we fail closed and recover?

## Recovery
- [ ] Can I roll back safely? (last known good version, feature flags)
- [ ] Do I need approval to scale up? (cost vs SLO tradeoff)
- [ ] Is there a runbook for this? (`docs/operations/runbooks/`)

## Communication
- [ ] Who needs to know right now? (incident channel, manager)
- [ ] When do I escalate? (MTTR > 15 min, P0 severity)
- [ ] What's the user-facing message? (status page update)

## Prevention
- [ ] What wakes me at 03:00, and how do I prevent that *today*?
- [ ] Should this alert fire during business hours instead? (not urgent)
- [ ] What test would have caught this before production?

---
**Use this to stay calm, act deliberately, and learn from every page.**
