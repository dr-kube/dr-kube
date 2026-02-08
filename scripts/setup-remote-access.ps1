# =============================================================================
# K8s 원격 접근 설정 스크립트 (Windows)
# Tailscale + kubeconfig 설정
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "🐳 K8s 원격 접근 설정 시작..." -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# 1. Tailscale 설치 확인
# -----------------------------------------------------------------------------
Write-Host "📦 1단계: Tailscale 설치 확인..." -ForegroundColor Yellow

$tailscaleInstalled = Get-Command tailscale -ErrorAction SilentlyContinue

if ($tailscaleInstalled) {
    Write-Host "✅ Tailscale 이미 설치됨" -ForegroundColor Green
} else {
    Write-Host "⏳ Tailscale 설치 중..." -ForegroundColor Yellow
    
    # winget으로 설치 시도
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Tailscale.Tailscale -e --accept-package-agreements --accept-source-agreements
    }
    # choco로 설치 시도
    elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install tailscale -y
    }
    else {
        Write-Host ""
        Write-Host "⚠️  자동 설치 실패. 수동 설치 필요:" -ForegroundColor Red
        Write-Host "   → https://tailscale.com/download/windows" -ForegroundColor White
        Write-Host ""
        Start-Process "https://tailscale.com/download/windows"
        Read-Host "설치 완료 후 Enter를 눌러주세요"
    }
    
    # PATH 새로고침
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# -----------------------------------------------------------------------------
# 2. Tailscale 로그인
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "🔐 2단계: Tailscale 로그인 확인..." -ForegroundColor Yellow

try {
    $status = tailscale status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Tailscale 로그인됨" -ForegroundColor Green
    } else {
        throw "Not logged in"
    }
} catch {
    Write-Host ""
    Write-Host "🔗 Tailscale 로그인이 필요합니다." -ForegroundColor Yellow
    Write-Host "   → 시스템 트레이의 Tailscale 아이콘 클릭 → Log in" -ForegroundColor White
    Write-Host ""
    
    # Tailscale 앱 실행
    Start-Process "tailscale-ipn" -ErrorAction SilentlyContinue
    
    Read-Host "로그인 완료 후 Enter를 눌러주세요"
}

# -----------------------------------------------------------------------------
# 3. Tailscale IP 확인
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "🌐 3단계: Tailscale IP 확인..." -ForegroundColor Yellow

$tailscaleIP = (tailscale ip -4 2>&1).Trim()

if ([string]::IsNullOrEmpty($tailscaleIP) -or $tailscaleIP -match "error") {
    Write-Host "❌ Tailscale IP를 가져올 수 없습니다." -ForegroundColor Red
    Write-Host "   → Tailscale이 연결되어 있는지 확인해주세요." -ForegroundColor White
    exit 1
}

Write-Host "✅ Tailscale IP: $tailscaleIP" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 4. kubeconfig 복사 (원격에서 가져온 경우 설정)
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "📄 4단계: kubeconfig 설정..." -ForegroundColor Yellow

$kubeconfigPath = "$env:USERPROFILE\.kube\config"
$kubeconfigRemote = "$env:USERPROFILE\.kube\config-remote"

# .kube 폴더 생성
$kubeDir = "$env:USERPROFILE\.kube"
if (-not (Test-Path $kubeDir)) {
    New-Item -ItemType Directory -Path $kubeDir -Force | Out-Null
}

if (Test-Path $kubeconfigRemote) {
    Write-Host "✅ 원격 kubeconfig 존재: $kubeconfigRemote" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "⚠️  원격 kubeconfig 파일이 필요합니다." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   K8s가 실행 중인 맥북에서:" -ForegroundColor White
    Write-Host "   1. ./setup-remote-access.sh 실행" -ForegroundColor White
    Write-Host "   2. ~/.kube/config-remote 파일을 이 PC로 복사" -ForegroundColor White
    Write-Host "   3. $kubeconfigRemote 에 저장" -ForegroundColor White
    Write-Host ""
}

# -----------------------------------------------------------------------------
# 5. 결과 출력
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "🎉 설정 완료!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 K8s 접근 방법:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. K8s가 실행 중인 맥북에서 config-remote 파일 복사" -ForegroundColor White
Write-Host "2. 이 PC에서 실행:" -ForegroundColor White
Write-Host ""
Write-Host '   $env:KUBECONFIG = "$env:USERPROFILE\.kube\config-remote"' -ForegroundColor White
Write-Host "   kubectl get nodes" -ForegroundColor White
Write-Host "   k9s" -ForegroundColor White
Write-Host ""
Write-Host "🔗 이 PC의 Tailscale IP: $tailscaleIP" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
