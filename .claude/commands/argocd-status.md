# ArgoCD 상태 확인

ArgoCD에서 관리하는 모든 Application의 상태를 확인합니다.

## 실행할 작업
```bash
argocd app list
```

각 Application의 Health와 Sync 상태를 확인하고 문제가 있으면 분석:
- **Health**: Healthy, Progressing, Degraded, Missing
- **Sync**: Synced, OutOfSync

문제가 있는 앱은 `argocd app get <app>` 로 상세 확인 후 원인 분석.
