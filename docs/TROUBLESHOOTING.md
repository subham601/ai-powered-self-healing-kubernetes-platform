# Troubleshooting

## Backend fails to fetch logs
- Ensure RBAC permissions for pods/log access
- Verify service account binding in Helm templates

## AI provider errors
- Ollama: confirm `ollama` service is reachable and model is available
- OpenAI: confirm secret `ai-healing-openai` exists

## ArgoCD sync issues
- Check ArgoCD Application namespace permissions
- Validate Helm values overrides and image tags

