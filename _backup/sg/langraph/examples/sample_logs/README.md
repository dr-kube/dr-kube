# 로그 예시 모음

다양한 에러 케이스에 대한 로그 예시입니다.

## 에러 카테고리별 예시

### 1. OOM (Out of Memory)
- `oom_grafana.txt`: Grafana Pod 메모리 부족
- `oom_prometheus.txt`: Prometheus Pod 메모리 부족
- `oom_multiple_pods.txt`: 여러 Pod 동시 OOM

### 2. CrashLoopBackOff
- `crashloop_config_error.txt`: 설정 오류로 인한 크래시
- `crashloop_image_error.txt`: 이미지 문제로 인한 크래시
- `crashloop_dependency.txt`: 의존성 문제로 인한 크래시

### 3. Config Error
- `config_yaml_syntax.txt`: YAML 문법 오류
- `config_missing_value.txt`: 필수 값 누락
- `config_invalid_format.txt`: 잘못된 형식

### 4. Resource Exhausted
- `resource_cpu_quota.txt`: CPU 쿼터 초과
- `resource_memory_quota.txt`: 메모리 쿼터 초과
- `resource_pod_quota.txt`: Pod 수 제한 초과

### 5. Network Error
- `network_connection_refused.txt`: 연결 거부
- `network_timeout.txt`: 타임아웃
- `network_dns_error.txt`: DNS 오류

### 6. Image Pull Error
- `image_pull_unauthorized.txt`: 인증 실패
- `image_not_found.txt`: 이미지 없음
- `image_pull_timeout.txt`: 이미지 풀 타임아웃

### 7. Pod Scheduling Error
- `scheduling_no_nodes.txt`: 노드 없음
- `scheduling_taint.txt`: Taint로 인한 스케줄링 실패
- `scheduling_affinity.txt`: Affinity 규칙 위반

### 8. 복합 에러
- `combined_oom_crashloop.txt`: OOM 후 CrashLoop
- `combined_network_config.txt`: 네트워크 + 설정 오류

## 사용 방법

```bash
# 특정 에러 케이스 테스트
python -m cli.main --log-file examples/sample_logs/oom_grafana.txt --dry-run

# 여러 케이스 일괄 테스트
for file in examples/sample_logs/*.txt; do
  python -m cli.main --log-file "$file" --dry-run
done
```

