FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 + gh CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY . .

# 비root 사용자
RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

EXPOSE 8080

# 웹훅 서버 실행
CMD ["python", "-m", "dr_kube.webhook"]
