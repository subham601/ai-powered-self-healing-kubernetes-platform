# Monitoring Stack

Production observability for the AI Self-Healing platform:

| Component | Purpose |
|-----------|---------|
| **Prometheus** | Metrics (CPU, memory, restarts, deployment health) |
| **Alertmanager** | Routes alerts to backend webhook (`/webhooks/alerts`) |
| **Loki** | Centralized pod logs |
| **Grafana** | Dashboards (Prometheus + Loki datasources) |

## Deploy with Helm

```bash
helm upgrade --install ai-healing-platform ./helm \
  --namespace ai-healing-system --create-namespace \
  --set monitoring.enabled=true
```

## Standalone configs

Reference manifests and configs live under:

- `monitoring/prometheus/` — Prometheus + alert rules + Alertmanager
- `monitoring/loki/` — Loki + Promtail
- `monitoring/grafana/` — Datasource provisioning
- `monitoring/dashboards/` — Grafana dashboard JSON

## Alert → self-healing loop

1. Prometheus fires alert (e.g. `PodCrashLooping`).
2. Alertmanager POSTs to `http://<backend>/webhooks/alerts`.
3. Backend runs `/analyze` logic and optional auto-heal (env: `SELF_HEAL_ALERT_AUTO_HEAL`).

Label alerts with `namespace` and `deployment` (or `pod`) for correct targeting.
