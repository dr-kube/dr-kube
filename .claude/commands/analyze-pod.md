# Pod 문제 분석

특정 Pod의 문제를 분석합니다.

## 인자
- $ARGUMENTS: <namespace>/<pod-name> 형식으로 전달

## 실행할 작업
1. Pod describe로 상세 정보 확인
2. 로그 확인 (이전 컨테이너 로그 포함)
3. 관련 이벤트 확인
4. 원인 분석 및 해결책 제시

```bash
# $ARGUMENTS 파싱
NAMESPACE=$(echo "$ARGUMENTS" | cut -d'/' -f1)
POD=$(echo "$ARGUMENTS" | cut -d'/' -f2)

kubectl describe pod $POD -n $NAMESPACE
kubectl logs $POD -n $NAMESPACE --tail=100
kubectl logs $POD -n $NAMESPACE --previous --tail=50 2>/dev/null || echo "이전 로그 없음"
kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$POD
```

분석 결과를 다음 형식으로 정리:
- **문제**: 무엇이 문제인지
- **원인**: 왜 발생했는지
- **해결책**: 어떻게 해결하는지 (kubectl 명령어 포함)
