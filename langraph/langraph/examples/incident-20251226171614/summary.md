# Incident Summary: incident-20251226171614

## 기본 정보
- **Incident ID**: incident-20251226171614
- **Error Category**: oom
- **Error Severity**: critical
- **Timestamp**: 20251226_171614

## 영향받는 애플리케이션
- grafana

## 근본 원인
grafana에서 메모리 부족이 발생했습니다.

## 승인된 액션
grafana의 메모리 리소스 제한을 증가시키세요 (values.yaml 수정)

## 커밋 메시지
```
fix: oom 에러 복구 - grafana의 메모리 리소스 제한을 증가시키세요 (values.yaml 수정)
```
