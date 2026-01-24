@echo off
chcp 65001 >nul
echo ================================================
echo AI DrKube - 로그 분석 도구
echo ================================================
echo.

REM 가상환경 확인
if not exist "venv\" (
    echo [오류] 가상환경이 없습니다. setup.bat을 먼저 실행해주세요.
    pause
    exit /b 1
)

REM 가상환경 활성화
call venv\Scripts\activate.bat

REM 도구 선택
echo 사용 가능한 도구:
echo   1. log_analysis_agent.py  - 로그 분석 에이전트
echo   2. error_classifier.py    - 에러 분류기
echo   3. root_cause_analyzer.py - 근본 원인 분석기
echo   4. alert_webhook_server.py - Alertmanager Webhook 서버
echo.

if "%~1"=="" (
    echo 사용법:
    echo   run_tools.bat log_analysis_agent.py [로그파일]
    echo   run_tools.bat error_classifier.py [로그파일]
    echo.
    echo 예시:
    echo   run_tools.bat log_analysis_agent.py tools\sample_error.log
    pause
    exit /b 0
)

REM 도구 실행
python tools\%*

pause
