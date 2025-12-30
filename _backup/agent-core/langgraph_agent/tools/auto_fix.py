"""
자동 수정 툴
다양한 Kubernetes 이슈를 자동으로 수정하는 도구 모음

이 파일에는 여러 종류의 문제를 자동으로 고치는 함수들이 있습니다.
"""
from typing import Optional, Tuple
from . import k8s


class AutoFixer:
    """
    자동 수정 도구
    
    다양한 Kubernetes 이슈를 감지하고 자동으로 수정합니다.
    각 메서드는 특정 문제 유형을 처리합니다.
    """
    
    def __init__(self, namespace: str = "default"):
        """
        Args:
            namespace: 작업할 네임스페이스
        """
        self.namespace = namespace
    
    def fix_oom_issue(
        self,
        pod_name: str,
        container_name: str,
        multiplier: float = 2.0
    ) -> Tuple[bool, str, dict]:
        """
        OOMKilled 이슈 자동 수정
        
        무엇을 하나요?
        1. 현재 메모리 설정 확인
        2. multiplier 배로 증가 (기본: 2배)
        3. Deployment에 패치 적용
        
        Args:
            pod_name: 파드 이름
            container_name: 컨테이너 이름
            multiplier: 메모리를 몇 배로 늘릴지 (기본: 2.0)
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        # 1. Deployment 찾기
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        # 2. 현재 설정 가져오기
        pod_details = k8s.get_pod_details(pod_name, self.namespace)
        if not pod_details:
            return False, "파드 정보를 가져올 수 없습니다", {}
        
        # 3. 새로운 메모리 계산
        current_limit = pod_details.get("memory_limit", "256Mi")
        current_request = pod_details.get("memory_request", "128Mi")
        
        # 메모리 문자열을 숫자로 변환
        limit_mi = self._parse_memory(current_limit)
        request_mi = self._parse_memory(current_request)
        
        # multiplier 배로 증가
        new_limit = self._format_memory(int(limit_mi * multiplier))
        new_request = self._format_memory(int(request_mi * multiplier))
        
        # 4. 패치 적용
        success, result = k8s.patch_deployment_resources(
            deployment_name=deployment_name,
            namespace=self.namespace,
            container_name=container_name,
            memory_limit=new_limit,
            memory_request=new_request
        )
        
        changes = {
            "old_limit": current_limit,
            "new_limit": new_limit,
            "old_request": current_request,
            "new_request": new_request,
            "multiplier": multiplier
        }
        
        if success:
            msg = f"메모리를 {current_limit} → {new_limit}로 증가시켰습니다"
            return True, msg, changes
        else:
            return False, f"수정 실패: {result}", changes
    
    def fix_cpu_throttling(
        self,
        pod_name: str,
        container_name: str,
        multiplier: float = 1.5
    ) -> Tuple[bool, str, dict]:
        """
        CPU Throttling 이슈 자동 수정
        
        CPU가 부족해서 느려지는 문제를 해결합니다.
        
        Args:
            pod_name: 파드 이름
            container_name: 컨테이너 이름
            multiplier: CPU를 몇 배로 늘릴지 (기본: 1.5)
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        pod_details = k8s.get_pod_details(pod_name, self.namespace)
        if not pod_details:
            return False, "파드 정보를 가져올 수 없습니다", {}
        
        # 현재 CPU 설정
        current_limit = pod_details.get("cpu_limit", "1000m")
        current_request = pod_details.get("cpu_request", "500m")
        
        # CPU를 밀리코어(m) 단위로 파싱
        limit_m = self._parse_cpu(current_limit)
        request_m = self._parse_cpu(current_request)
        
        # multiplier 배로 증가
        new_limit = f"{int(limit_m * multiplier)}m"
        new_request = f"{int(request_m * multiplier)}m"
        
        success, result = k8s.patch_deployment_resources(
            deployment_name=deployment_name,
            namespace=self.namespace,
            container_name=container_name,
            cpu_limit=new_limit,
            cpu_request=new_request
        )
        
        changes = {
            "old_limit": current_limit,
            "new_limit": new_limit,
            "old_request": current_request,
            "new_request": new_request,
            "multiplier": multiplier
        }
        
        if success:
            msg = f"CPU를 {current_limit} → {new_limit}로 증가시켰습니다"
            return True, msg, changes
        else:
            return False, f"수정 실패: {result}", changes
    
    def fix_image_pull_error(
        self,
        pod_name: str,
        new_image: Optional[str] = None
    ) -> Tuple[bool, str, dict]:
        """
        ImagePullBackOff 이슈 자동 수정
        
        이미지를 다운로드하지 못하는 문제를 해결합니다.
        새 이미지를 지정하거나, imagePullPolicy를 변경합니다.
        
        Args:
            pod_name: 파드 이름
            new_image: 새로운 이미지 (선택사항)
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        if new_image:
            # 새 이미지로 업데이트
            success, result = k8s.run_kubectl(
                ["set", "image", f"deployment/{deployment_name}",
                 f"*={new_image}"],
                namespace=self.namespace
            )
            changes = {"new_image": new_image}
            msg = f"이미지를 {new_image}로 업데이트했습니다" if success else result
        else:
            # imagePullPolicy를 IfNotPresent로 변경 (로컬 이미지 사용 시도)
            msg = "수동으로 이미지를 확인해주세요"
            success = False
            changes = {}
        
        return success, msg, changes
    
    def restart_deployment(
        self,
        pod_name: str
    ) -> Tuple[bool, str, dict]:
        """
        Deployment 재시작
        
        CrashLoopBackOff 등의 문제에서 간단히 재시작을 시도합니다.
        
        Args:
            pod_name: 파드 이름
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        success, result = k8s.rollout_restart("deployment", deployment_name, self.namespace)
        
        changes = {"deployment": deployment_name, "action": "restart"}
        
        if success:
            msg = f"Deployment {deployment_name}을 재시작했습니다"
            return True, msg, changes
        else:
            return False, f"재시작 실패: {result}", changes
    
    def scale_deployment(
        self,
        pod_name: str,
        replicas: int
    ) -> Tuple[bool, str, dict]:
        """
        Deployment 스케일 조정
        
        파드 개수를 늘리거나 줄입니다.
        
        Args:
            pod_name: 파드 이름
            replicas: 원하는 파드 개수
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        success, result = k8s.run_kubectl(
            ["scale", f"deployment/{deployment_name}",
             f"--replicas={replicas}"],
            namespace=self.namespace
        )
        
        changes = {"deployment": deployment_name, "replicas": replicas}
        
        if success:
            msg = f"Deployment {deployment_name}을 {replicas}개로 스케일했습니다"
            return True, msg, changes
        else:
            return False, f"스케일 실패: {result}", changes
    
    def add_node_selector(
        self,
        pod_name: str,
        node_selector: dict[str, str]
    ) -> Tuple[bool, str, dict]:
        """
        NodeSelector 추가
        
        특정 노드에서만 파드가 실행되도록 설정합니다.
        
        Args:
            pod_name: 파드 이름
            node_selector: 노드 선택 조건
                예: {"disktype": "ssd", "zone": "us-west-1a"}
        
        Returns:
            (성공여부, 메시지, 수정내역)
        """
        deployment_name = k8s.get_deployment_for_pod(pod_name, self.namespace)
        if not deployment_name:
            return False, "Deployment를 찾을 수 없습니다", {}
        
        # kubectl patch로 nodeSelector 추가
        import json
        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "nodeSelector": node_selector
                    }
                }
            }
        }
        
        success, result = k8s.run_kubectl(
            ["patch", "deployment", deployment_name,
             "-p", json.dumps(patch),
             "--type=strategic"],
            namespace=self.namespace
        )
        
        changes = {"node_selector": node_selector}
        
        if success:
            msg = f"NodeSelector를 추가했습니다: {node_selector}"
            return True, msg, changes
        else:
            return False, f"NodeSelector 추가 실패: {result}", changes
    
    # 헬퍼 메서드들
    def _parse_memory(self, mem_str: str) -> int:
        """메모리 문자열을 Mi 단위 정수로 변환"""
        if not mem_str:
            return 128
        mem_str = mem_str.strip()
        if mem_str.endswith("Gi"):
            return int(float(mem_str[:-2]) * 1024)
        elif mem_str.endswith("Mi"):
            return int(float(mem_str[:-2]))
        elif mem_str.endswith("Ki"):
            return int(float(mem_str[:-2]) / 1024)
        else:
            try:
                return int(int(mem_str) / (1024 * 1024))
            except:
                return 128
    
    def _format_memory(self, mi_value: int) -> str:
        """Mi 값을 적절한 단위로 포맷"""
        if mi_value >= 1024:
            return f"{mi_value // 1024}Gi"
        return f"{mi_value}Mi"
    
    def _parse_cpu(self, cpu_str: str) -> int:
        """CPU 문자열을 밀리코어 단위로 변환"""
        if not cpu_str:
            return 1000
        cpu_str = cpu_str.strip()
        if cpu_str.endswith("m"):
            return int(cpu_str[:-1])
        else:
            # 코어 단위면 밀리코어로 변환 (1 = 1000m)
            return int(float(cpu_str) * 1000)


# 간편 함수들
def quick_fix_oom(pod_name: str, namespace: str = "default", container: str = "") -> bool:
    """
    OOM 이슈 빠른 수정
    
    사용 예:
        quick_fix_oom("my-pod", "default", "my-container")
    """
    fixer = AutoFixer(namespace)
    success, msg, _ = fixer.fix_oom_issue(pod_name, container)
    print(msg)
    return success


def quick_restart(pod_name: str, namespace: str = "default") -> bool:
    """
    파드 빠른 재시작
    
    사용 예:
        quick_restart("my-pod", "default")
    """
    fixer = AutoFixer(namespace)
    success, msg, _ = fixer.restart_deployment(pod_name)
    print(msg)
    return success
