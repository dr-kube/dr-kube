@echo off
chcp 65001 >nul
echo ================================================
echo AI DrKube - Kubernetes 장애 분석 Agent
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

REM 인자가 없으면 샘플 파일 목록 표시
if "%~1"=="" (
    echo ============================================================
    echo 사용 가능한 샘플 이슈 파일
    echo ============================================================
    echo.
    echo [리소스 관련]
    echo   1. issues\sample_oom.json               - Out Of Memory
    echo   2. issues\sample_cpu_throttle.json      - CPU Throttle
    echo.
    echo [설정/구성 관련]
    echo   3. issues\sample_image_pull.json        - 이미지 Pull 실패
    echo   4. issues\sample_configmap_missing.json - ConfigMap 누락
    echo   5. issues\sample_pvc_pending.json       - PVC Pending
    echo.
    echo [헬스체크 관련]
    echo   6. issues\sample_liveness_probe_fail.json - Liveness Probe 실패
    echo.
    echo [네트워크 관련]
    echo   7. issues\sample_network_policy.json    - 네트워크 연결 실패
    echo   8. issues\sample_dns_resolution.json    - DNS 해석 실패
    echo.
    echo [스케줄링/권한 관련]
    echo   9. issues\sample_node_not_ready.json    - 노드 스케줄링 실패
    echo  10. issues\sample_rbac_permission.json   - RBAC 권한 부족
    echo.
    echo [애플리케이션 관련]
    echo  11. issues\sample_app_crash.json         - 앱 크래시
    echo.
    echo ============================================================
    echo 사용법:
    echo   run.bat issues\sample_oom.json         # 간결한 출력
    echo   run.bat issues\sample_oom.json -v      # 상세한 출력
    echo ============================================================
    echo.
    pause
    exit /b 0
)

REM CLI 실행 (모든 인자 전달)
cd src
python -m cli analyze ..\%*
cd ..

pause
