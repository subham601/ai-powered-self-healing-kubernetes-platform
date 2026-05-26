# TODO

- [x] Fix GitHub Actions CI to build+push BOTH backend and frontend Docker images to their correct DockerHub repos/tags.
- [x] Update CI to bump the correct Helm image tags for backend AND frontend (not only backend).
- [x] Verify Helm templates already deploy frontend on :8085 and backend on :9000.
- [x] Run a Helm template render (dry-run) to confirm the correct images are referenced.
- [ ] Harden CI/CD: auto-bump Helm image tag after successful Docker push using immutable Git SHA (no YAML parsing).
- [x] Make Helm update logic idempotent (commit only if values change) and update both backendImage.tag + frontendImage.tag robustly.
- [x] Harden ArgoCD sync trigger with `curl --fail/--retry`.

- [ ] Next phase: Enable real Kubernetes execution layer gated by existing guardrails.
  - [ ] Implement restart (deployment rollout restart via patch)
  - [ ] Implement rollback (deployment revision tracking)
  - [ ] Implement scale (deployment replicas patch)
- [ ] Add rollback automation
  - [ ] Store previous deployment revisions
  - [ ] Safe rollback on failure detection
- [ ] Connect Prometheus + Loki signals
  - [ ] Prometheus metrics fetch
  - [ ] Loki log fetch
  - [ ] Feed into AI analyzer as incident packet
- [ ] Add event-driven triggering
  - [ ] CrashLoopBackOff / OOMKilled / high restart count triggers
  - [ ] Webhook or polling controller
- [ ] Improve safety system
  - [ ] Deployment cooldown per deployment
  - [ ] Max global remediation limit
  - [ ] Audit log for every action

