# Architecture

## Components
- **frontend/**: dashboard UI
- **backend/**: FastAPI AI analyzer + ChatOps + remediation executor
- **monitoring/**: Prometheus/Grafana/Loki config and dashboards
- **helm/**: Helm chart for deploying platform components
- **argocd/**: ArgoCD manifests to deploy isolated namespace resources

## Data Flow
1. Monitoring stack ingests logs & metrics.
2. Backend detects failure patterns and queries logs.
3. AI classifier summarizes root cause and proposes remediation.
4. Self-healing actions are executed (restart/rollback/scale/sync) with safety constraints.
5. Frontend surfaces recommendations and actions.

