# DR-Kube 에이전트 실행

이슈 파일로 에이전트를 실행합니다.

## 인자
- $ARGUMENTS: 이슈 파일 경로 (예: issues/sample_oom.json)

## 실행할 작업
```bash
cd agent
source ../venv/bin/activate
python -m cli analyze $ARGUMENTS
```

실행 결과를 확인하고 분석이 정확한지 검토해주세요.
