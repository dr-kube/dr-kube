"""
로그 수집 모듈
로컬 파일 또는 외부 소스(Kubernetes Pod 로그 등)에서 로그를 수집합니다.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class LogCollector:
    """로그 수집 클래스"""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        초기화
        
        Args:
            kubeconfig_path: Kubernetes config 파일 경로 (None이면 기본 경로 사용)
        """
        self.kubeconfig_path = kubeconfig_path
        self.k8s_client = None
        
        # Kubernetes 클라이언트 초기화 시도
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_incluster_config()  # 클러스터 내부에서 실행 시
        except config.ConfigException:
            try:
                config.load_kube_config()  # 로컬 kubeconfig 사용
            except Exception as e:
                logger.warning(f"Kubernetes 클라이언트 초기화 실패: {e}")
        
        try:
            self.k8s_client = client.CoreV1Api()
        except Exception as e:
            logger.warning(f"Kubernetes API 클라이언트 생성 실패: {e}")
    
    def collect_from_file(self, file_path: str) -> List[str]:
        """
        로컬 파일에서 로그 수집
        
        Args:
            file_path: 로그 파일 경로
            
        Returns:
            로그 라인 리스트
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"파일을 찾을 수 없습니다: {file_path}")
                return []
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            logger.info(f"파일에서 {len(lines)}줄의 로그를 수집했습니다: {file_path}")
            return [line.strip() for line in lines if line.strip()]
        
        except Exception as e:
            logger.error(f"파일 읽기 오류: {e}")
            return []
    
    def collect_from_directory(self, dir_path: str, pattern: str = "*.log") -> Dict[str, List[str]]:
        """
        디렉토리에서 여러 로그 파일 수집
        
        Args:
            dir_path: 디렉토리 경로
            pattern: 파일 패턴 (기본값: *.log)
            
        Returns:
            파일명을 키로 하는 로그 딕셔너리
        """
        logs = {}
        try:
            path = Path(dir_path)
            if not path.exists() or not path.is_dir():
                logger.error(f"디렉토리를 찾을 수 없습니다: {dir_path}")
                return logs
            
            for log_file in path.glob(pattern):
                file_logs = self.collect_from_file(str(log_file))
                if file_logs:
                    logs[log_file.name] = file_logs
            
            logger.info(f"디렉토리에서 {len(logs)}개의 파일을 수집했습니다: {dir_path}")
            return logs
        
        except Exception as e:
            logger.error(f"디렉토리 읽기 오류: {e}")
            return {}
    
    def collect_from_pod(self, pod_name: str, namespace: str = "default", 
                        container: Optional[str] = None, tail_lines: int = 100) -> List[str]:
        """
        Kubernetes Pod에서 로그 수집
        
        Args:
            pod_name: Pod 이름
            namespace: 네임스페이스 (기본값: default)
            container: 컨테이너 이름 (None이면 첫 번째 컨테이너)
            tail_lines: 수집할 최근 로그 라인 수
            
        Returns:
            로그 라인 리스트
        """
        if not self.k8s_client:
            logger.error("Kubernetes 클라이언트가 초기화되지 않았습니다")
            return []
        
        try:
            # Pod 정보 조회
            pod = self.k8s_client.read_namespaced_pod(pod_name, namespace)
            
            # 컨테이너 이름 결정
            if not container:
                if pod.spec.containers:
                    container = pod.spec.containers[0].name
                else:
                    logger.error(f"Pod에 컨테이너가 없습니다: {pod_name}")
                    return []
            
            # 로그 수집
            logs = self.k8s_client.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                timestamps=False
            )
            
            log_lines = logs.split('\n') if logs else []
            logger.info(f"Pod에서 {len(log_lines)}줄의 로그를 수집했습니다: {pod_name}/{container}")
            return [line.strip() for line in log_lines if line.strip()]
        
        except ApiException as e:
            logger.error(f"Kubernetes API 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"Pod 로그 수집 오류: {e}")
            return []
    
    def get_pod_metadata(self, pod_name: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """
        Pod의 메타데이터 수집 (라벨, 서비스 정보 등)
        
        Args:
            pod_name: Pod 이름
            namespace: 네임스페이스
            
        Returns:
            Pod 메타데이터 딕셔너리 또는 None
        """
        if not self.k8s_client:
            return None
        
        try:
            pod = self.k8s_client.read_namespaced_pod(pod_name, namespace)
            
            metadata = {
                "pod_name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "labels": pod.metadata.labels or {},
                "node_name": pod.spec.node_name,
                "phase": pod.status.phase,
                "containers": [c.name for c in pod.spec.containers] if pod.spec.containers else []
            }
            
            # 서비스 정보 찾기 (라벨 기반)
            if pod.metadata.labels:
                # app, app.kubernetes.io/name 등의 라벨로 서비스 식별
                service_name = (
                    pod.metadata.labels.get("app") or
                    pod.metadata.labels.get("app.kubernetes.io/name") or
                    pod.metadata.labels.get("k8s-app") or
                    None
                )
                if service_name:
                    metadata["service_name"] = service_name
            
            return metadata
        
        except Exception as e:
            logger.warning(f"Pod 메타데이터 수집 실패: {e}")
            return None
    
    def get_pods_metadata_by_label(self, label_selector: str, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        라벨 셀렉터로 여러 Pod의 메타데이터 수집
        
        Args:
            label_selector: 라벨 셀렉터
            namespace: 네임스페이스
            
        Returns:
            Pod 메타데이터 리스트
        """
        if not self.k8s_client:
            return []
        
        try:
            pods = self.k8s_client.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )
            
            metadata_list = []
            for pod in pods.items:
                metadata = self.get_pod_metadata(pod.metadata.name, namespace)
                if metadata:
                    metadata_list.append(metadata)
            
            return metadata_list
        
        except Exception as e:
            logger.warning(f"Pod 메타데이터 수집 실패: {e}")
            return []
    
    def extract_pod_info_from_logs(self, logs: List[str], namespace: str = "default") -> Optional[Dict[str, Any]]:
        """
        로그 내용에서 Pod 이름을 추출하고 메타데이터 수집
        
        Args:
            logs: 로그 라인 리스트
            namespace: 네임스페이스 (기본값: default)
            
        Returns:
            Pod 메타데이터 딕셔너리 또는 None
        """
        if not self.k8s_client:
            return None
        
        # 로그에서 Pod 이름 패턴 찾기
        # 일반적인 패턴: pod-name-xxxxx, pod_name, podName 등
        pod_name_patterns = [
            r'pod[_-]?([a-z0-9-]+)',  # pod-name-12345
            r'pod[:\s]+([a-z0-9-]+)',  # pod: name-12345
            r'\[pod[:\s]+([a-z0-9-]+)\]',  # [pod: name-12345]
            r'pod[=]([a-z0-9-]+)',  # pod=name-12345
        ]
        
        found_pods = set()
        for log_line in logs:
            for pattern in pod_name_patterns:
                matches = re.findall(pattern, log_line, re.IGNORECASE)
                for match in matches:
                    # Pod 이름 형식 검증 (일반적인 Kubernetes Pod 이름 패턴)
                    if re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$', match):
                        found_pods.add(match)
        
        # 첫 번째로 찾은 Pod의 메타데이터 조회
        for pod_name in found_pods:
            try:
                metadata = self.get_pod_metadata(pod_name, namespace)
                if metadata:
                    logger.info(f"로그에서 Pod 이름 추출 및 메타데이터 수집: {pod_name}")
                    return metadata
            except Exception as e:
                logger.debug(f"Pod {pod_name} 메타데이터 조회 실패: {e}")
                continue
        
        # Pod 이름을 찾지 못한 경우, 로그에서 서비스 이름이나 앱 이름 추출 시도
        service_patterns = [
            r'service[:\s=]+([a-z0-9-]+)',
            r'app[:\s=]+([a-z0-9-]+)',
            r'application[:\s=]+([a-z0-9-]+)',
        ]
        
        found_services = set()
        for log_line in logs:
            for pattern in service_patterns:
                matches = re.findall(pattern, log_line, re.IGNORECASE)
                found_services.update(matches)
        
        if found_services:
            # 서비스 이름만 있는 경우, 기본 메타데이터 생성
            service_name = list(found_services)[0]
            logger.info(f"로그에서 서비스 이름 추출: {service_name}")
            return {
                "service_name": service_name,
                "namespace": namespace,
                "source": "extracted_from_logs"
            }
        
        return None
    
    def collect_from_pods_by_label(self, label_selector: str, namespace: str = "default",
                                   container: Optional[str] = None, tail_lines: int = 100) -> Dict[str, List[str]]:
        """
        라벨 셀렉터로 여러 Pod에서 로그 수집
        
        Args:
            label_selector: 라벨 셀렉터 (예: "app=myapp")
            namespace: 네임스페이스
            container: 컨테이너 이름
            tail_lines: 수집할 최근 로그 라인 수
            
        Returns:
            Pod 이름을 키로 하는 로그 딕셔너리
        """
        if not self.k8s_client:
            logger.error("Kubernetes 클라이언트가 초기화되지 않았습니다")
            return {}
        
        logs = {}
        try:
            # 라벨로 Pod 목록 조회
            pods = self.k8s_client.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )
            
            for pod in pods.items:
                pod_logs = self.collect_from_pod(
                    pod.metadata.name,
                    namespace,
                    container,
                    tail_lines
                )
                if pod_logs:
                    logs[pod.metadata.name] = pod_logs
            
            logger.info(f"라벨 셀렉터로 {len(logs)}개의 Pod에서 로그를 수집했습니다: {label_selector}")
            return logs
        
        except ApiException as e:
            logger.error(f"Kubernetes API 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"Pod 로그 수집 오류: {e}")
            return {}
    
    def collect_from_stdin(self) -> List[str]:
        """
        표준 입력에서 로그 수집
        
        Returns:
            로그 라인 리스트
        """
        try:
            lines = []
            for line in sys.stdin:
                lines.append(line.strip())
            logger.info(f"표준 입력에서 {len(lines)}줄의 로그를 수집했습니다")
            return [line for line in lines if line.strip()]
        except Exception as e:
            logger.error(f"표준 입력 읽기 오류: {e}")
            return []