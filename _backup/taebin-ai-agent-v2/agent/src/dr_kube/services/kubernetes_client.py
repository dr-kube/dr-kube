"""Kubernetes 클라이언트"""
import os
import subprocess
import json
from typing import Optional, Dict, Any, List
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from src.tools.logger import get_logger

logger = get_logger(__name__)


class KubernetesClient:
    """Kubernetes API 클라이언트"""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Kubernetes 클라이언트 초기화
        
        Args:
            kubeconfig_path: kubeconfig 파일 경로 (없으면 기본 경로 사용)
        """
        self.kubeconfig_path = kubeconfig_path or os.getenv("KUBECONFIG_PATH")
        
        try:
            if self.kubeconfig_path and os.path.exists(self.kubeconfig_path):
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                # 기본 kubeconfig 경로 또는 인클러스터 설정
                try:
                    config.load_incluster_config()
                    logger.info("인클러스터 설정 로드")
                except:
                    config.load_kube_config()
                    logger.info("기본 kubeconfig 로드")
            
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Kubernetes 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Kubernetes 클라이언트 초기화 실패: {str(e)}")
            raise
    
    def get_pod_status(self, namespace: str, pod_name: str) -> Dict[str, Any]:
        """
        Pod 상태 조회
        
        Args:
            namespace: 네임스페이스
            pod_name: Pod 이름
            
        Returns:
            Pod 상태 정보
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            return {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ready": all(condition.status == "True" for condition in pod.status.conditions or []),
                "restart_count": sum(container.restart_count for container in pod.status.container_statuses or []),
            }
        except ApiException as e:
            logger.error(f"Pod 상태 조회 실패: {str(e)}")
            raise
    
    def get_deployment_status(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        """
        Deployment 상태 조회
        
        Args:
            namespace: 네임스페이스
            deployment_name: Deployment 이름
            
        Returns:
            Deployment 상태 정보
        """
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            return {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
            }
        except ApiException as e:
            logger.error(f"Deployment 상태 조회 실패: {str(e)}")
            raise
    
    def get_resource_status(
        self,
        namespace: str,
        resource_type: str,
        resource_name: str
    ) -> str:
        """
        리소스 상태 조회 (범용)
        
        Args:
            namespace: 네임스페이스
            resource_type: 리소스 타입 (Pod, Deployment 등)
            resource_name: 리소스 이름
            
        Returns:
            리소스 상태 문자열
        """
        try:
            if resource_type.lower() == "pod":
                status = self.get_pod_status(namespace, resource_name)
                return f"Pod {resource_name}: {status['status']}, Ready: {status['ready']}, Restarts: {status['restart_count']}"
            elif resource_type.lower() == "deployment":
                status = self.get_deployment_status(namespace, resource_name)
                return f"Deployment {resource_name}: {status['ready_replicas']}/{status['replicas']} ready"
            else:
                # kubectl 명령어로 조회
                return self._kubectl_get_status(namespace, resource_type, resource_name)
        except Exception as e:
            logger.error(f"리소스 상태 조회 실패: {str(e)}")
            return f"상태 조회 실패: {str(e)}"
    
    def _kubectl_get_status(
        self,
        namespace: str,
        resource_type: str,
        resource_name: str
    ) -> str:
        """
        kubectl 명령어로 리소스 상태 조회
        
        Args:
            namespace: 네임스페이스
            resource_type: 리소스 타입
            resource_name: 리소스 이름
            
        Returns:
            리소스 상태 문자열
        """
        try:
            cmd = [
                "kubectl",
                "get",
                resource_type.lower(),
                resource_name,
                "-n",
                namespace,
                "-o",
                "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl 명령어 실행 실패: {str(e)}")
            return f"kubectl 실행 실패: {str(e)}"
    
    def execute_kubectl_command(self, command: str) -> str:
        """
        kubectl 명령어 실행
        
        Args:
            command: kubectl 명령어 (예: "get pods -n default")
            
        Returns:
            명령어 실행 결과
        """
        try:
            cmd = ["kubectl"] + command.split()
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"kubectl 명령어 실행 성공: {command}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl 명령어 실행 실패: {str(e)}")
            raise
    
    def list_all_namespaces(self) -> List[str]:
        """
        모든 네임스페이스 목록 조회
        
        Returns:
            네임스페이스 이름 리스트
        """
        try:
            namespaces = self.core_v1.list_namespace()
            namespace_list = [ns.metadata.name for ns in namespaces.items]
            logger.info(f"네임스페이스 목록 조회 완료: {len(namespace_list)}개")
            return namespace_list
        except ApiException as e:
            logger.error(f"네임스페이스 목록 조회 실패: {str(e)}")
            raise
    
    def get_pods_all_namespaces(self) -> List[Dict[str, Any]]:
        """
        모든 네임스페이스의 Pod 조회
        
        Returns:
            Pod 정보 리스트
        """
        try:
            pods = self.core_v1.list_pod_for_all_namespaces()
            pod_list = [
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ready": all(condition.status == "True" for condition in pod.status.conditions or []),
                }
                for pod in pods.items
            ]
            logger.info(f"전체 Pod 조회 완료: {len(pod_list)}개")
            return pod_list
        except ApiException as e:
            logger.error(f"전체 Pod 조회 실패: {str(e)}")
            raise
    
    def get_resource_status_all_namespaces(
        self,
        resource_type: str,
        resource_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        모든 네임스페이스에서 리소스 상태 조회
        
        Args:
            resource_type: 리소스 타입 (Pod, Deployment 등)
            resource_name: 리소스 이름 (없으면 모든 리소스)
            
        Returns:
            {namespace: status_string} 딕셔너리
        """
        try:
            result = {}
            
            if resource_type.lower() == "pod":
                pods = self.core_v1.list_pod_for_all_namespaces()
                for pod in pods.items:
                    if resource_name is None or pod.metadata.name == resource_name:
                        ready = all(condition.status == "True" for condition in pod.status.conditions or [])
                        restart_count = sum(container.restart_count for container in pod.status.container_statuses or [])
                        status = f"Pod {pod.metadata.name}: {pod.status.phase}, Ready: {ready}, Restarts: {restart_count}"
                        result[pod.metadata.namespace] = status
            elif resource_type.lower() == "deployment":
                deployments = self.apps_v1.list_deployment_for_all_namespaces()
                for deployment in deployments.items:
                    if resource_name is None or deployment.metadata.name == resource_name:
                        ready_replicas = deployment.status.ready_replicas or 0
                        replicas = deployment.spec.replicas
                        status = f"Deployment {deployment.metadata.name}: {ready_replicas}/{replicas} ready"
                        result[deployment.metadata.namespace] = status
            else:
                # kubectl 명령어 사용
                cmd = ["kubectl", "get", resource_type.lower(), "--all-namespaces", "-o", "json"]
                if resource_name:
                    cmd.insert(-2, resource_name)
                
                try:
                    result_subprocess = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    data = json.loads(result_subprocess.stdout)
                    
                    if "items" in data:
                        for item in data["items"]:
                            ns = item["metadata"]["namespace"]
                            name = item["metadata"]["name"]
                            status_str = f"{resource_type} {name}: {item.get('status', {}).get('phase', 'Unknown')}"
                            result[ns] = status_str
                except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
                    logger.warning(f"kubectl로 전체 namespace 조회 실패: {str(e)}")
                    return {}
            
            logger.info(f"전체 namespace 리소스 조회 완료: {len(result)}개 namespace")
            return result
            
        except Exception as e:
            logger.error(f"전체 네임스페이스 리소스 조회 실패: {str(e)}")
            return {}