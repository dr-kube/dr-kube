# DR-Kube Agent

Kubernetes 이슈 분석 에이전트

## 빠른 시작

프로젝트 루트에서 실행:

```bash
make agent-setup         # 환경 설정
vi agent/.env            # API 키 설정
make agent-run           # 실행
```

## Make 명령어 (프로젝트 루트에서)

```bash
make help              # 도움말
make agent-setup       # 환경 설정
make agent-run         # 기본 이슈 분석
make agent-oom         # OOM 이슈 분석
make agent-cpu         # CPU Throttle 분석
make agent-run-all     # 모든 샘플 분석
make agent-clean       # 가상환경 삭제
```

특정 이슈 파일 분석:
```bash
make agent-run ISSUE=issues/sample_image_pull.json
```

## 구조

```
agent/
├── cli.py              # CLI 진입점
├── dr_kube/            # 메인 에이전트 코드
│   ├── graph.py        # LangGraph 워크플로우
│   ├── llm.py          # LLM 프로바이더
│   ├── prompts.py      # 프롬프트 템플릿
│   └── state.py        # 상태 정의
├── issues/             # 샘플 이슈 파일 (11개)
├── requirements.txt
└── .env.example
```

## LLM 설정

`.env` 파일:

| 프로바이더 | 설정 | 비고 |
|-----------|------|------|
| Gemini | `LLM_PROVIDER=gemini` | 클라우드. API 키 필요 |
| Ollama | `LLM_PROVIDER=ollama` | 로컬, 무료. `ollama pull qwen2.5:14b` 필요 |
