# TODO

## Audit-safe self-healing execution (ConfigMap ledger)
- [ ] Implement an audit ledger + guard state persistence (cooldown + max retries) using a Kubernetes ConfigMap.
- [ ] Update `Remediator` so it *records a decision* before any mutation and fails closed if the audit write fails.
- [ ] Replace process-local `_guard_state` with persisted values from the ConfigMap.
- [ ] Make remediation action resolution defensive: missing/invalid remediation => treat as `noop`.
- [ ] Improve response shape to include planned vs executed actions (executed empty when blocked).
- [ ] Run `python -m compileall backend/ai_self_healing_backend` to ensure no syntax errors.

