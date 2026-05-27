# AI-Powered Self-Healing Kubernetes Platform

Production-oriented platform that monitors Kubernetes workloads, analyzes logs with AI (OpenAI or Ollama), and safely remediates failures (restart / rollback / scale) with audit-first guardrails and GitOps delivery.

## Features

- **Observability**: Prometheus metrics, Loki logs, Grafana dashboards
- **AI analysis**: Structured JSON root-cause + remediation recommendation
- **Self-healing**: Deployment-level actions with cooldown, confidence gating, ConfigMap audit ledger
- **ChatOps API**: `POST /analyze`, `/restart`, `/rollback`, `/scale`
- **Alert webhook**: `POST /webhooks/alerts` (Alertmanager → auto-heal)
- **GitOps**: Argo CD + Helm
- **CI/CD**: GitHub Actions (build, push, bump Helm tags)

## Folder structure

```
.
├── .github/workflows/ci-cd.yml    # CI: test, build images, bump Helm tags
├── argocd/                        # Argo CD Application + AppProject
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── ai_self_healing_backend/
│       ├── app/                   # FastAPI routes + webhooks
│       ├── ai/                    # Ollama / OpenAI provider
│       ├── k8s/                  # K8s client, executor, Loki client
│       └── service/               # Analyzer, remediator, audit ledger
├── frontend/                      # React ChatOps UI (Vite + nginx)
├── helm/                          # Helm chart (app + optional monitoring)
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── files/                     # Embedded monitoring configs
│   └── templates/
├── monitoring/                    # Prometheus / Loki / Grafana reference configs
│   ├── prometheus/
│   ├── loki/
│   ├── grafana/
│   └── dashboards/
└── docs/                          # Architecture, deployment, GitOps, CI/CD
```

## Quick start (local backend)

```bash
cd backend
pip install -r requirements.txt
export AI_PROVIDER=ollama OLLAMA_BASE_URL=http://localhost:11434
uvicorn ai_self_healing_backend.app.main:app --host 0.0.0.0 --port 9000
```

```bash
curl -X POST http://localhost:9000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"namespace":"ai-healing-system","workload":"my-deployment","workload_kind":"deployment","dry_run":true}'
```

## Deploy on Kubernetes (Helm)

```bash
kubectl create namespace ai-healing-system
helm upgrade --install ai-healing-platform ./helm \
  --namespace ai-healing-system \
  --set monitoring.enabled=true
```

## GitOps (Argo CD)

```bash
kubectl apply -f argocd/namespace.yaml
kubectl apply -f argocd/appproject.yaml
# Edit argocd/application.yaml repoURL, then:
kubectl apply -f argocd/application.yaml
```

## ChatOps endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| POST | `/analyze` | AI log analysis (+ optional `auto_heal`) |
| POST | `/restart` | Restart deployment |
| POST | `/rollback` | Rollback deployment |
| POST | `/scale` | Scale deployment |
| POST | `/webhooks/alerts` | Alertmanager → analyze/heal |

## Safety

- Allowed namespaces (`SELF_HEAL_ALLOWED_NAMESPACES`)
- Confidence gating (medium/high for auto-heal)
- Cooldown + max retries (`_guard_state`)
- **Audit ledger**: PENDING → execute → SUCCESS/FAILED (fail-closed if audit write fails)

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [GitOps](docs/GITOPS.md)
- [CI/CD](docs/CI_CD.md)
- [Monitoring](monitoring/README.md)

## License

MIT (add `LICENSE` as needed for your organization).
