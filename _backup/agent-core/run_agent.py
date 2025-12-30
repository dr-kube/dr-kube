#!/usr/bin/env python3
"""
dr-kube Agent 실행 스크립트
"""
import os
import sys

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# GEMINI_API_KEY 확인
if not os.getenv("GEMINI_API_KEY"):
    print("❌ GEMINI_API_KEY 환경변수를 설정해주세요.")
    print("   export GEMINI_API_KEY=your-api-key")
    print("   또는 .env 파일에 추가")
    sys.exit(1)

from langgraph_agent.cli import main
sys.exit(main())
