from kubernetes import client, config
from typing import List, Dict, Any, Optional
import yaml


class K8sClient:
    def __init__(self, kubeconfig_path: Optional[str] = None):
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                config.load_incluster_config()
            except:
                config.load_kube_config()

        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_oomkilled_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """OOMKilled 상태인 파드들을 찾습니다."""
        pods = self.v1.list_namespaced_pod(namespace)
        oomkilled_pods = []

        for pod in pods.items:
            for container_status in pod.status.container_statuses or []:
                if container_status.state.terminated:
                    if container_status.state.terminated.reason == "OOMKilled":
                        oomkilled_pods.append({
                            "name": pod.metadata.name,
                            "namespace": pod.metadata.namespace,
                            "container": container_status.name,
                            "restart_count": container_status.restart_count,
                            "terminated_at": str(container_status.state.terminated.finished_at)
                        })
                elif container_status.last_state.terminated:
                    if container_status.last_state.terminated.reason == "OOMKilled":
                        oomkilled_pods.append({
                            "name": pod.metadata.name,
                            "namespace": pod.metadata.namespace,
                            "container": container_status.name,
                            "restart_count": container_status.restart_count,
                            "last_terminated_at": str(container_status.last_state.terminated.finished_at)
                        })

        return oomkilled_pods

    def get_pod_details(self, pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """특정 파드의 상세 정보를 가져옵니다."""
        pod = self.v1.read_namespaced_pod(pod_name, namespace)

        containers_info = []
        for container in pod.spec.containers:
            resources = container.resources
            containers_info.append({
                "name": container.name,
                "image": container.image,
                "requests": {
                    "memory": resources.requests.get("memory") if resources.requests else None,
                    "cpu": resources.requests.get("cpu") if resources.requests else None
                },
                "limits": {
                    "memory": resources.limits.get("memory") if resources.limits else None,
                    "cpu": resources.limits.get("cpu") if resources.limits else None
                }
            })

        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "labels": pod.metadata.labels,
            "containers": containers_info,
            "node": pod.spec.node_name,
            "status": pod.status.phase
        }

    def get_pod_logs(self, pod_name: str, container_name: str,
                     namespace: str = "default", tail_lines: int = 100) -> str:
        """파드의 로그를 가져옵니다."""
        try:
            logs = self.v1.read_namespaced_pod_log(
                pod_name,
                namespace,
                container=container_name,
                tail_lines=tail_lines
            )
            return logs
        except Exception as e:
            return f"Error fetching logs: {str(e)}"

    def get_pod_events(self, pod_name: str, namespace: str = "default") -> List[Dict[str, Any]]:
        """파드 관련 이벤트를 가져옵니다."""
        events = self.v1.list_namespaced_event(
            namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )

        event_list = []
        for event in events.items:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "first_timestamp": str(event.first_timestamp),
                "last_timestamp": str(event.last_timestamp)
            })

        return event_list

    def get_deployment_yaml(self, pod_name: str, namespace: str = "default") -> Optional[str]:
        """파드가 속한 Deployment의 YAML을 가져옵니다."""
        try:
            pod = self.v1.read_namespaced_pod(pod_name, namespace)

            # ReplicaSet을 통해 Deployment 찾기
            if pod.metadata.owner_references:
                for owner in pod.metadata.owner_references:
                    if owner.kind == "ReplicaSet":
                        rs = self.apps_v1.read_namespaced_replica_set(owner.name, namespace)
                        if rs.metadata.owner_references:
                            for rs_owner in rs.metadata.owner_references:
                                if rs_owner.kind == "Deployment":
                                    deployment = self.apps_v1.read_namespaced_deployment(
                                        rs_owner.name, namespace
                                    )
                                    return yaml.dump(deployment.to_dict(), default_flow_style=False)
        except Exception as e:
            return f"Error fetching deployment: {str(e)}"

        return None


# LangChain 도구로 사용할 함수들
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = K8sClient()
    return _client


def get_oomkilled_pods(namespace: str = "default") -> str:
    """OOMKilled 상태인 파드들을 찾습니다."""
    client = _get_client()
    pods = client.get_oomkilled_pods(namespace)
    if not pods:
        return "No OOMKilled pods found."
    return yaml.dump(pods, default_flow_style=False)


def get_pod_details(pod_name: str, namespace: str = "default") -> str:
    """특정 파드의 상세 정보를 가져옵니다."""
    client = _get_client()
    details = client.get_pod_details(pod_name, namespace)
    return yaml.dump(details, default_flow_style=False)


def get_pod_logs(pod_name: str, container_name: str, namespace: str = "default") -> str:
    """파드의 로그를 가져옵니다."""
    client = _get_client()
    return client.get_pod_logs(pod_name, container_name, namespace)


def get_pod_events(pod_name: str, namespace: str = "default") -> str:
    """파드 관련 이벤트를 가져옵니다."""
    client = _get_client()
    events = client.get_pod_events(pod_name, namespace)
    return yaml.dump(events, default_flow_style=False)


def update_pod_resources(pod_name: str, namespace: str,
                        container_name: str, memory_limit: str) -> str:
    """파드의 리소스 제한을 업데이트하기 위한 정보를 제공합니다."""
    client = _get_client()
    deployment_yaml = client.get_deployment_yaml(pod_name, namespace)

    if deployment_yaml:
        return f"""
To update resources for pod {pod_name}, modify the Deployment YAML:

{deployment_yaml}

Update the container '{container_name}' resources.limits.memory to '{memory_limit}'
"""
    else:
        return f"Could not find Deployment for pod {pod_name}"
