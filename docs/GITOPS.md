# GitOps Workflow (ArgoCD + Helm)

## Summary
- Helm renders Kubernetes manifests.
- ArgoCD watches the Helm chart source.
- GitHub Actions updates Helm values (image tag) and commits changes.
- ArgoCD auto-sync deploys new versions into an isolated namespace.

## Isolation Guarantees
- Separate ArgoCD Application (`ai-healing-platform`)
- Separate namespace (`ai-healing-system`)
- No dependency on the existing ecommerce GitOps project

