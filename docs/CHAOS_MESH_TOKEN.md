# Chaos Mesh Dashboard 토큰 관리

## 토큰 생성

Chaos Mesh Dashboard 접근을 위한 RBAC 토큰은 다음 명령어로 생성합니다:

```bash
kubectl create token chaos-dashboard -n chaos-mesh --duration=87600h
```

## 토큰 저장

생성된 토큰은 Kubernetes Secret으로 저장하여 관리합니다:

```bash
TOKEN=$(kubectl create token chaos-dashboard -n chaos-mesh --duration=87600h)
kubectl create secret generic chaos-dashboard-token -n chaos-mesh \
  --from-literal=token="$TOKEN"
```

## 토큰 조회

저장된 토큰을 조회하는 방법:

```bash
# 터미널에 출력
kubectl get secret chaos-dashboard-token -n chaos-mesh -o jsonpath='{.data.token}' | base64 -d

# macOS 클립보드에 복사
kubectl get secret chaos-dashboard-token -n chaos-mesh -o jsonpath='{.data.token}' | base64 -d | pbcopy

# Linux 클립보드에 복사 (xclip)
kubectl get secret chaos-dashboard-token -n chaos-mesh -o jsonpath='{.data.token}' | base64 -d | xclip -selection clipboard
```

## 토큰 갱신

토큰이 만료되거나 새 토큰이 필요한 경우:

```bash
# 기존 Secret 삭제
kubectl delete secret chaos-dashboard-token -n chaos-mesh

# 새 토큰으로 Secret 재생성
TOKEN=$(kubectl create token chaos-dashboard -n chaos-mesh --duration=87600h)
kubectl create secret generic chaos-dashboard-token -n chaos-mesh \
  --from-literal=token="$TOKEN"
```

## 참고사항

- 토큰은 10년(87600h) 동안 유효합니다
- ServiceAccount는 `chaos-dashboard`를 사용합니다
- 토큰은 Chaos Mesh Dashboard의 RBAC 인증에 사용됩니다
- Name 필드는 선택사항이며, 원하는 이름(예: `admin`)을 입력할 수 있습니다
