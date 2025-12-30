# Grafana Alloy 설정 문서

## 📋 개요

Grafana Alloy는 Kubernetes 클러스터의 로그, 메트릭, 트레이스를 수집하고 Grafana 스택(Loki, Prometheus, Tempo)으로 전송하는 통합 수집 에이전트입니다.

## 🔧 이미지 설정

### Image Configuration
```yaml
image:
  registry: "docker.io"           # Docker 레지스트리
  repository: grafana/alloy       # 저장소명
  tag: null                        # 버전 (null = Chart appVersion 사용)
  digest: null                     # SHA256 다이제스트 (tag 대신 사용 가능)
  pullPolicy: IfNotPresent         # 이미지 풀 정책
  pullSecrets: []                  # Private 레지스트리용 시크릿
```

### 설정 변경 방법

**다른 레지스트리 사용 (예: 프라이빗 레지스트리)**:
```yaml
image:
  registry: "gcr.io"
  repository: my-project/alloy
  tag: "1.0.0"
  pullSecrets:
    - name: gcr-secret
```

**특정 버전 지정**:
```yaml
image:
  tag: "v1.4.0"  # null 대신 버전 지정
```

## 🎯 컨트롤러 타입

```yaml
controller:
  type: daemonset  # 모든 노드에 배포
```

### DaemonSet vs Deployment
- **DaemonSet**: 모든 노드에 Alloy 포드 배포 (메트릭/로그 수집에 권장)
- **Deployment**: 특정 개수의 포드만 배포 (CPU/메모리 절약)

**DaemonSet을 선택한 이유**:
- 모든 노드의 로그를 수집 가능
- 노드별 로컬 수집으로 네트워크 최소화
- 높은 가용성

## 📊 주요 설정

### 로깅 설정
```alloy
logging {
  level  = "info"      # 로그 레벨 (debug, info, warn, error)
  format = "logfmt"    # 로그 포맷
}
```

### Kubernetes 디스커버리
```alloy
discovery.kubernetes "pods" {
  role = "pod"
  
  selectors {
    role  = "pod"
    field = "spec.nodeName=" + coalesce(sys.env("HOSTNAME"), constants.hostname)
  }
}
```
- 각 노드의 로컬 포드만 발견 (효율성 증대)
- DaemonSet과 함께 사용되어 중복 수집 방지

### Loki 연동
```alloy
loki.source.kubernetes "pods" {
  targets    = discovery.kubernetes.pods.targets
  forward_to = [loki.write.local.receiver]
}

loki.write "local" {
  endpoint {
    url = sys.env("LOKI_URL")
  }
}
```

**환경변수**:
```yaml
extraEnv:
  - name: LOKI_URL
    value: "http://loki-gateway.monitoring.svc.cluster.local/loki/api/v1/push"
```

## 🔐 RBAC 및 보안

**자동 설정 (기본값)**:
- ServiceAccount 생성
- ClusterRole & ClusterRoleBinding 자동 생성
- Pod 디스커버리를 위한 필수 권한 포함

```yaml
rbac:
  create: true              # RBAC 리소스 자동 생성
serviceAccount:
  create: true              # ServiceAccount 자동 생성
```

## 📈 리소스 설정 (선택)

```yaml
# 필요시 추가
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi
```

## 📚 참고 자료

- [Grafana Alloy 공식 문서](https://grafana.com/docs/alloy/latest/)
- [Kubernetes 통합 설정](https://grafana.com/docs/alloy/latest/configure/kubernetes/)
- [Loki 소스 설정](https://grafana.com/docs/alloy/latest/reference/components/loki.source.kubernetes/)
