# DAY2_WORK

## 2026-01-08
- Loki Push 프로토콜(payload protobuf+snappy)을 수신해 내부에서 JSON 형태(로그 라인+라벨)로 변환하도록 디코더 추가.
- `/loki/api/v1/push` 라우트가 JSON만 받던 로직을 protobuf/JSON 모두 처리하도록 변경.
- Loki protobuf 디코딩을 위해 `protobuf`, `python-snappy` 의존성 추가.
- protobuf 최신 버전에서 `MessageFactory.GetPrototype` 미지원 이슈를 `GetMessageClass`로 우회.
