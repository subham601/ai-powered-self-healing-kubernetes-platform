# TODO - AI-Powered Self-Healing Kubernetes Platform

- [ ] Create root project README + docs scaffold
- [ ] Create backend (FastAPI) service code scaffold
- [ ] Create backend AI analyzer provider abstraction (Ollama/OpenAI)
- [ ] Create backend Kubernetes log + pod analysis utilities
- [ ] Create ChatOps API endpoints: /analyze, /restart, /rollback, /scale
- [ ] Create frontend dashboard scaffold
- [ ] Create Helm chart (Chart.yaml, values.yaml, templates) for backend/frontend
- [ ] Create monitoring configs + Grafana dashboards (CPU/memory/restarts/CrashLoopBackOff/etc.)
- [ ] Create ArgoCD manifests (AppProject + Application) isolated to ai-healing-system
- [ ] Create GitHub Actions workflows (build/push/version bump/update Helm/commit/argocd sync)
- [ ] Create production hardening manifests (HPA, Ingress, NetworkPolicy, probes)
- [ ] Add deployment/troubleshooting docs
- [ ] Lint + template Helm for smoke checks

