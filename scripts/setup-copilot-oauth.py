#!/usr/bin/env python3
"""GitHub Copilot OAuth Device Flow 토큰 발급 스크립트

사전 준비:
  GitHub Settings > Developer Settings > OAuth Apps > New OAuth App
  - Application name: dr-kube-agent (아무거나)
  - Homepage URL: http://localhost
  - Callback URL: http://localhost
  Client ID를 복사해서 아래 실행 시 입력

사용법:
  python3 scripts/setup-copilot-oauth.py
  또는
  python3 scripts/setup-copilot-oauth.py --client-id <CLIENT_ID>
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
import urllib.parse


DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPE = "copilot"


def post_json(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_device_code(client_id: str) -> dict:
    return post_json(DEVICE_CODE_URL, {"client_id": client_id, "scope": SCOPE})


def poll_token(client_id: str, device_code: str, interval: int) -> str:
    while True:
        time.sleep(interval)
        result = post_json(TOKEN_URL, {
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        error = result.get("error")
        if error == "authorization_pending":
            print(".", end="", flush=True)
            continue
        elif error == "slow_down":
            interval += 5
            print("s", end="", flush=True)
            continue
        elif error == "expired_token":
            print("\n[오류] 코드가 만료됐어요. 다시 실행해주세요.")
            sys.exit(1)
        elif error == "access_denied":
            print("\n[오류] 사용자가 거부했어요.")
            sys.exit(1)
        elif "access_token" in result:
            return result["access_token"]
        else:
            print(f"\n[오류] 예상치 못한 응답: {result}")
            sys.exit(1)


def update_k8s_secret(token: str) -> None:
    """K8s Secret의 github-token 키를 OAuth 토큰으로 업데이트"""
    import base64
    encoded = base64.b64encode(token.encode()).decode()
    patch = json.dumps({
        "data": {"github-token": encoded}
    })
    result = subprocess.run(
        ["kubectl", "--context", "kind-dr-kube",
         "patch", "secret", "dr-kube-agent-secrets",
         "-n", "monitoring",
         "--type", "merge",
         "-p", patch],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[완료] K8s Secret 업데이트 성공")
    else:
        print(f"[오류] Secret 업데이트 실패: {result.stderr}")
        print(f"수동으로 업데이트하세요:\n  kubectl patch secret dr-kube-agent-secrets -n monitoring "
              f"--type merge -p '{{\"data\":{{\"github-token\":\"{encoded}\"}}}}'")


def restart_agent() -> None:
    result = subprocess.run(
        ["kubectl", "--context", "kind-dr-kube",
         "rollout", "restart", "deployment/dr-kube-agent", "-n", "monitoring"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[완료] 에이전트 재시작 완료")
    else:
        print(f"[경고] 재시작 실패: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="GitHub Copilot OAuth 토큰 발급")
    parser.add_argument("--client-id", help="GitHub OAuth App Client ID")
    parser.add_argument("--no-k8s", action="store_true", help="K8s Secret 자동 업데이트 건너뜀")
    args = parser.parse_args()

    client_id = args.client_id
    if not client_id:
        print("GitHub OAuth App Client ID를 입력하세요.")
        print("없다면: https://github.com/settings/applications/new 에서 생성")
        print("  - Homepage URL: http://localhost")
        print("  - Callback URL: http://localhost")
        client_id = input("Client ID: ").strip()
        if not client_id:
            print("[오류] Client ID가 필요해요.")
            sys.exit(1)

    print("\n[1/3] Device Code 요청 중...")
    resp = get_device_code(client_id)
    if "error" in resp:
        print(f"[오류] {resp}")
        sys.exit(1)

    user_code = resp["user_code"]
    verification_uri = resp["verification_uri"]
    device_code = resp["device_code"]
    interval = resp.get("interval", 5)

    print(f"\n[2/3] 브라우저에서 인증해주세요:")
    print(f"  URL  : {verification_uri}")
    print(f"  Code : {user_code}")
    print("\n인증 대기 중", end="", flush=True)

    token = poll_token(client_id, device_code, interval)

    print(f"\n\n[3/3] 토큰 발급 성공!")
    print(f"  Token: {token[:20]}...{token[-4:]}")

    if not args.no_k8s:
        print("\nK8s Secret 자동 업데이트 중...")
        update_k8s_secret(token)
        print("에이전트 재시작 중...")
        restart_agent()
    else:
        print(f"\n토큰을 수동으로 저장하세요:\n  {token}")


if __name__ == "__main__":
    main()
