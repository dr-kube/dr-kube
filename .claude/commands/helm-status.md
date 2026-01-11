# Helm 릴리즈 상태 확인

설치된 모든 Helm 차트의 상태를 확인합니다.

## 실행할 작업
```bash
helm list -A
```

각 릴리즈의 상태를 확인하고 문제가 있으면 알려주세요.
- deployed: 정상
- failed: 배포 실패
- pending-*: 진행 중

failed 상태인 릴리즈가 있다면 `helm history <release> -n <namespace>`로 상세 확인.
