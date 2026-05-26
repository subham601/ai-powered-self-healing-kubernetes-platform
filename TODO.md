# TODO

- [x] Fix GitHub Actions CI to build+push BOTH backend and frontend Docker images to their correct DockerHub repos/tags.
- [x] Update CI to bump the correct Helm image tags for backend AND frontend (not only backend).
- [x] Verify Helm templates already deploy frontend on :8085 and backend on :9000.
- [x] Run a Helm template render (dry-run) to confirm the correct images are referenced.
- [x] Harden CI/CD: auto-bump Helm image tag after successful Docker push using immutable Git SHA tag (no YAML parsing).
- [x] Make Helm update logic idempotent (commit only if values change) and update both backendImage.tag + frontendImage.tag robustly.
- [x] Harden ArgoCD sync trigger with `curl --fail --retry`.


