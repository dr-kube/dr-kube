"""ArgoCD 연동 모듈"""
import json
import subprocess
from typing import Dict, List, Optional


def get_applications() -> List[Dict]:
    """ArgoCD Application 목록 가져오기"""
    try:
        result = subprocess.run(
            ["argocd", "app", "list", "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return []
    except json.JSONDecodeError:
        return []


def get_application_detail(app_name: str) -> Optional[Dict]:
    """특정 Application 상세 정보"""
    try:
        result = subprocess.run(
            ["argocd", "app", "get", app_name, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def get_unhealthy_apps() -> List[Dict]:
    """비정상 상태의 Application 필터링"""
    apps = get_applications()
    unhealthy = []

    for app in apps:
        health = app.get("status", {}).get("health", {}).get("status", "")
        sync = app.get("status", {}).get("sync", {}).get("status", "")

        if health != "Healthy" or sync != "Synced":
            unhealthy.append(
                {
                    "name": app.get("metadata", {}).get("name"),
                    "namespace": app.get("metadata", {}).get("namespace"),
                    "health": health,
                    "sync": sync,
                    "message": app.get("status", {})
                    .get("conditions", [{}])[0]
                    .get("message", ""),
                }
            )

    return unhealthy


def get_k8s_pods(namespace: str = "all") -> List[Dict]:
    """K8s Pod 상태 수집"""
    try:
        cmd = ["kubectl", "get", "pods", "-o", "json"]
        if namespace != "all":
            cmd.extend(["-n", namespace])
        else:
            cmd.append("-A")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("items", [])
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def get_k8s_events(namespace: str = "all", limit: int = 50) -> List[Dict]:
    """K8s Event 수집 (최근 것부터)"""
    try:
        cmd = ["kubectl", "get", "events", "-o", "json", "--sort-by=.lastTimestamp"]
        if namespace != "all":
            cmd.extend(["-n", namespace])
        else:
            cmd.append("-A")

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        events = data.get("items", [])
        return events[-limit:] if len(events) > limit else events
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def get_pod_logs(pod_name: str, namespace: str, tail: int = 100) -> str:
    """특정 Pod의 로그 가져오기"""
    try:
        result = subprocess.run(
            [
                "kubectl",
                "logs",
                pod_name,
                "-n",
                namespace,
                f"--tail={tail}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""
