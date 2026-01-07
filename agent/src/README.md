# 생성된 구조
agent/
  src/
    dr_kube/
      __init__.py
      state.py      # 상태 정의 (20줄)
      llm.py        # LLM 프로바이더 (30줄)
      prompts.py    # 프롬프트 템플릿 (25줄)
      graph.py      # LangGraph 그래프 (90줄)
    cli.py          # CLI (45줄)
    requirements.txt
    pyproject.toml
    .env.example
  issues/
    sample_oom.json
    sample_image_pull.json
    sample_cpu_throttle.json
사용 방법

# 1. 디렉토리 이동
cd agent/src

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 설정 (.env 파일 생성)
cp .env.example .env
# LLM_PROVIDER=ollama 또는 gemini 설정

# 4. 실행
python -m cli analyze ../issues/sample_oom.json
LLM 설정
.env 파일에서 선택:
LLM_PROVIDER=ollama + OLLAMA_MODEL=llama3.2 (로컬, 무료)
LLM_PROVIDER=gemini + GEMINI_API_KEY=xxx (클라우드)
Ollama 사용 시 먼저 ollama pull llama3.2 실행 필요합니다.