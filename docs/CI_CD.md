# CI/CD Pipeline

## GitHub Actions
- Build Docker image for backend + frontend (as applicable)
- Push to DockerHub with incrementing tags (v1, v2, v3, ...)
- Update Helm values `image.tag`
- Commit changes to GitHub
- Trigger ArgoCD sync

