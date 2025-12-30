"""
Kubernetes API 도구
kubectl 명령어 실행 및 K8s 리소스 조회/수정
"""
import subprocess
import json
import yaml
from typing import Optional


def run_kubectl(args: list[str], namespace: Optional[str] = None) -> tuple[bool, str]:
    """kubectl 명령어 실행"""
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_pods_with_issues(namespace: str = "default") -> list[dict]:
    """
    문제가 있는 파드들을 찾아서 리스트로 반환합니다.
    
    어떻게 동작하나요?
    1. kubectl get pods 명령으로 모든 파드 정보를 JSON으로 가져옵니다
    2. 각 파드의 상태를 확인합니다
    3. 문제가 있으면 이슈 정보를 리스트에 추가합니다
    
    Args:
        namespace: 확인할 네임스페이스 (기본값: "default")
    
    Returns:
        문제가 있는 파드들의 정보 리스트
        예: [{"type": "oomkilled", "pod_name": "my-pod", ...}, ...]
    """
    # kubectl get pods -n <namespace> -o json 명령 실행
    success, output = run_kubectl(
        ["get", "pods", "-o", "json"],
        namespace=namespace
    )
    
    # 명령 실패하면 빈 리스트 반환
    if not success:
        return []
    
    # JSON 문자열을 파이썬 딕셔너리로 변환
    pods_data = json.loads(output)
    # 발견된 이슈들을 저장할 리스트
    issues = []
    
    for pod in pods_data.get("items", []):
        pod_name = pod["metadata"]["name"]
        pod_namespace = pod["metadata"]["namespace"]
        
        # containerStatuses 확인
        container_statuses = pod.get("status", {}).get("containerStatuses", [])
        
        for cs in container_statuses:
            container_name = cs["name"]
            restart_count = cs.get("restartCount", 0)
            
            # OOMKilled 체크
            last_state = cs.get("lastState", {})
            terminated = last_state.get("terminated", {})
            if terminated.get("reason") == "OOMKilled":
                issues.append({
                    "type": "oomkilled",
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "container_name": container_name,
                    "restart_count": restart_count,
                    "message": f"Container {container_name} was OOMKilled"
                })
            
            # CrashLoopBackOff 체크
            waiting = cs.get("state", {}).get("waiting", {})
            if waiting.get("reason") == "CrashLoopBackOff":
                issues.append({
                    "type": "crashloop",
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "container_name": container_name,
                    "restart_count": restart_count,
                    "message": waiting.get("message", "CrashLoopBackOff")
                })
            
            # ImagePullBackOff 체크
            if waiting.get("reason") in ["ImagePullBackOff", "ErrImagePull"]:
                issues.append({
                    "type": "imagepull",
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "container_name": container_name,
                    "restart_count": restart_count,
                    "message": waiting.get("message", "Image pull failed")
                })
        
        # 4. Pending 상태 체크 (파드가 시작되지 못하고 대기 중)
        # Pending 상태는 리소스 부족, 노드 선택 불가 등의 이유로 발생
        if pod.get("status", {}).get("phase") == "Pending":
            conditions = pod.get("status", {}).get("conditions", [])
            message = "Pod is pending"
            # conditions에서 스케줄링 실패 원인 찾기
            for cond in conditions:
                if cond.get("type") == "PodScheduled" and cond.get("status") == "False":
                    message = cond.get("message", message)
            
            issues.append({
                "type": "pending",
                "pod_name": pod_name,
                "namespace": pod_namespace,
                "container_name": None,
                "restart_count": 0,
                "message": message
            })
        
        # 5. NodeNotReady 상태 체크 (노드에 문제가 있는 경우)
        node_name = pod.get("spec", {}).get("nodeName")
        if node_name:
            # 파드의 상태가 Running이 아니고 노드 관련 이슈가 있는지 확인
            pod_conditions = pod.get("status", {}).get("conditions", [])
            for cond in pod_conditions:
                if cond.get("type") == "Ready" and cond.get("status") == "False":
                    reason = cond.get("reason", "")
                    if "Node" in reason:
                        issues.append({
                            "type": "node_issue",
                            "pod_name": pod_name,
                            "namespace": pod_namespace,
                            "container_name": None,
                            "restart_count": 0,
                            "message": f"Node issue: {cond.get('message', reason)}"
                        })
    
    return issues


def get_pod_details(pod_name: str, namespace: str = "default") -> Optional[dict]:
    """파드 상세 정보 조회"""
    success, output = run_kubectl(
        ["get", "pod", pod_name, "-o", "json"],
        namespace=namespace
    )
    
    if not success:
        return None
    
    pod = json.loads(output)
    
    # 첫 번째 컨테이너의 리소스 정보 추출
    containers = pod.get("spec", {}).get("containers", [])
    if not containers:
        return None
    
    container = containers[0]
    resources = container.get("resources", {})
    requests = resources.get("requests", {})
    limits = resources.get("limits", {})
    
    return {
        "name": pod["metadata"]["name"],
        "namespace": pod["metadata"]["namespace"],
        "labels": pod["metadata"].get("labels", {}),
        "memory_request": requests.get("memory"),
        "memory_limit": limits.get("memory"),
        "cpu_request": requests.get("cpu"),
        "cpu_limit": limits.get("cpu"),
        "node": pod["spec"].get("nodeName"),
        "status": pod["status"]["phase"]
    }


def get_pod_events(pod_name: str, namespace: str = "default") -> list[dict]:
    """파드 관련 이벤트 조회"""
    success, output = run_kubectl(
        ["get", "events", "--field-selector", f"involvedObject.name={pod_name}", "-o", "json"],
        namespace=namespace
    )
    
    if not success:
        return []
    
    events_data = json.loads(output)
    events = []
    
    for event in events_data.get("items", []):
        events.append({
            "type": event.get("type"),
            "reason": event.get("reason"),
            "message": event.get("message"),
            "count": event.get("count", 1),
            "last_timestamp": event.get("lastTimestamp")
        })
    
    return events


def get_pod_logs(pod_name: str, namespace: str = "default", 
                 container: Optional[str] = None, tail: int = 50) -> str:
    """파드 로그 조회"""
    args = ["logs", pod_name, "--tail", str(tail)]
    if container:
        args.extend(["-c", container])
    
    # 이전 컨테이너 로그 시도 (OOMKilled 경우)
    args.append("--previous")
    success, output = run_kubectl(args, namespace=namespace)
    
    if not success:
        # 이전 로그 없으면 현재 로그 시도
        args.remove("--previous")
        success, output = run_kubectl(args, namespace=namespace)
    
    return output if success else f"Failed to get logs: {output}"


def get_deployment_for_pod(pod_name: str, namespace: str = "default") -> Optional[str]:
    """파드가 속한 Deployment 이름 조회"""
    success, output = run_kubectl(
        ["get", "pod", pod_name, "-o", "jsonpath={.metadata.ownerReferences[0].name}"],
        namespace=namespace
    )
    
    if not success:
        return None
    
    # ReplicaSet 이름에서 Deployment 이름 추출
    rs_name = output.strip()
    if not rs_name:
        return None
    
    # ReplicaSet의 owner 조회
    success, output = run_kubectl(
        ["get", "rs", rs_name, "-o", "jsonpath={.metadata.ownerReferences[0].name}"],
        namespace=namespace
    )
    
    return output.strip() if success else None


def patch_deployment_resources(
    deployment_name: str,
    namespace: str,
    container_name: str,
    memory_limit: Optional[str] = None,
    memory_request: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    cpu_request: Optional[str] = None
) -> tuple[bool, str]:
    """Deployment 리소스 패치"""
    patch = {"spec": {"template": {"spec": {"containers": []}}}}
    
    container_patch = {"name": container_name, "resources": {"limits": {}, "requests": {}}}
    
    if memory_limit:
        container_patch["resources"]["limits"]["memory"] = memory_limit
    if memory_request:
        container_patch["resources"]["requests"]["memory"] = memory_request
    if cpu_limit:
        container_patch["resources"]["limits"]["cpu"] = cpu_limit
    if cpu_request:
        container_patch["resources"]["requests"]["cpu"] = cpu_request
    
    patch["spec"]["template"]["spec"]["containers"].append(container_patch)
    
    patch_json = json.dumps(patch)
    
    return run_kubectl(
        ["patch", "deployment", deployment_name, "-p", patch_json, "--type=strategic"],
        namespace=namespace
    )


def rollout_restart(resource_type: str, name: str, namespace: str = "default") -> tuple[bool, str]:
    """Rollout restart 실행"""
    return run_kubectl(
        ["rollout", "restart", resource_type, name],
        namespace=namespace
    )
