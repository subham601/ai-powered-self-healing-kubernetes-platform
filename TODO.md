# TODO

## Audit-safe self-healing execution (ConfigMap ledger)
- [x] Implement a persistent audit ledger using a Kubernetes ConfigMap (PENDING -> execute -> SUCCESS/FAILED, fail-closed, max 3 retries).
- [ ] Replace process-local `_guard_state` with persisted values from the ConfigMap.
- [ ] Make remediation action resolution defensive: missing/invalid remediation => treat as `noop`.
- [ ] Improve response shape to include planned vs executed actions (executed empty when blocked).
- [x] Run `python -m compileall backend/ai_self_healing_backend` to ensure no syntax errors.

## Platform enhancements
- [x] Loki log collector + deployment pod resolution
- [x] Alertmanager webhook auto-healing
- [x] Helm monitoring stack (Prometheus, Grafana, Loki, Alertmanager)
- [x] ChatOps frontend UI
- [ ] Promtail DaemonSet for cluster-wide log shipping (optional)
- [ ] kube-state-metrics for full Prometheus alert rules
