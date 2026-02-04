# DR-Kube 웹서버 Dockerfile
# 경량화된 멀티스테이지 빌드

# Stage 1: 빌드 스테이지
FROM python:3.11-slim as builder

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /build

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: 런타임 스테이지
FROM python:3.11-slim

# 런타임 의존성 (필요한 경우)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 비root 사용자 생성
RUN useradd -m -u 1000 drkube && \
    mkdir -p /app && \
    chown -R drkube:drkube /app

# 작업 디렉토리 설정
WORKDIR /app

# 빌드 스테이지에서 Python 패키지 복사
COPY --from=builder /root/.local /home/drkube/.local

# 프로젝트 파일 복사
COPY --chown=drkube:drkube tools/ ./tools/
COPY --chown=drkube:drkube .env* ./

# 비root 사용자로 전환
USER drkube

# PATH에 로컬 Python 패키지 경로 추가
ENV PATH=/home/drkube/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 포트 노출
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 서버 실행
CMD ["python", "-m", "tools.dr_kube", "--host", "0.0.0.0", "--port", "8080"]

