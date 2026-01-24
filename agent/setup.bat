@echo off
chcp 65001 >nul
echo ================================================
echo AI DrKube 설정 스크립트 (Windows)
echo ================================================
echo.

REM Python 버전 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 https://www.python.org/downloads/ 에서 설치해주세요.
    pause
    exit /b 1
)

echo [1/4] Python 버전 확인...
python --version

echo.
echo [2/4] 가상환경 생성...
if not exist "venv\" (
    python -m venv venv
    echo 가상환경이 생성되었습니다.
) else (
    echo 가상환경이 이미 존재합니다.
)

echo.
echo [3/4] 가상환경 활성화 및 패키지 설치...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r src\requirements.txt

echo.
echo [4/4] 환경 설정 확인...
if not exist ".env" (
    echo .env 파일이 이미 존재합니다.
) else (
    echo .env 파일이 존재합니다.
)

echo.
echo ================================================
echo 설정이 완료되었습니다!
echo ================================================
echo.
echo 실행 방법:
echo   1. run.bat             - CLI로 샘플 이슈 분석
echo   2. run_tools.bat       - 로그 분석 도구 실행
echo.
pause
