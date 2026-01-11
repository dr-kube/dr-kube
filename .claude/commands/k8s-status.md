# K8s 클러스터 상태 확인

현재 K8s 클러스터의 전체 상태를 확인합니다.

## 실행할 작업
1. 모든 네임스페이스의 Pod 상태 확인
2. 문제가 있는 Pod 식별 (CrashLoopBackOff, Error, Pending 등)
3. 최근 이벤트 확인
4. 결과를 한국어로 요약

```bash
kubectl get pods -A
kubectl get events -A --sort-by='.lastTimestamp' | tail -20
```

문제가 발견되면 원인과 해결 방법을 간단히 제시해주세요.
