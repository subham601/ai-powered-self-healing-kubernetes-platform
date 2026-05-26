# Deployment Guide

## Prerequisites
- Kubernetes cluster
- ArgoCD installed
- DockerHub credentials for CI publishing

## Steps
1. Configure DockerHub repo: `shubham379/ai-self-healing-platform`
2. Create Kubernetes namespace: `ai-healing-system`
3. Create secrets:
   - `ai-healing-openai` (if using OpenAI)
4. Install monitoring stack (Helm subchart or separate manifests)
5. Apply ArgoCD manifests from `argocd/`

## Verification
- Check `backend` and `frontend` services
- Validate AI analyzer endpoint via `/docs`

