"""
Chaos Engineering 도구
Chaos Mesh를 사용한 카오스 실험 관리
"""
import json
import subprocess
from typing import Optional, Dict, List
from .k8s import run_kubectl


def is_chaos_mesh_installed() -> bool:
    """
    Chaos Mesh가 설치되어 있는지 확인
    
    Returns:
        True if Chaos Mesh CRDs are available
    """
    success, result = run_kubectl(["api-resources", "--api-group=chaos-mesh.org"])
    return "podchaos" in result.lower() if success and result else False


def check_chaos_mesh_prerequisites() -> tuple[bool, str]:
    """
    Chaos Mesh 사용을 위한 사전 조건 확인
    
    Returns:
        (성공 여부, 메시지)
    """
    if not is_chaos_mesh_installed():
        return False, """
❌ Chaos Mesh가 설치되어 있지 않습니다.

설치 방법:
1. Helm으로 설치:
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace

2. kubectl로 설치:
   curl -sSL https://mirrors.chaos-mesh.org/latest/install.sh | bash

자세한 내용: https://chaos-mesh.org/docs/quick-start/
"""
    
    return True, "✅ Chaos Mesh 사용 가능"


class ChaosExperiment:
    """Chaos Mesh 실험 관리"""
    
    def __init__(self, namespace: str = "default"):
        """
        초기화
        
        Args:
            namespace: 대상 네임스페이스
        """
        self.namespace = namespace
    
    def create_pod_kill_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        duration: str = "30s",
        mode: str = "one"
    ) -> tuple[bool, str]:
        """
        Pod Kill Chaos 생성
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택 (예: {"app": "myapp"})
            duration: 실험 지속 시간 (예: "30s", "5m")
            mode: one (하나), all (전체), fixed (고정 개수), random-max-percent
            
        Returns:
            (성공 여부, 메시지)
        """
        selector_str = ",".join([f"{k}={v}" for k, v in label_selector.items()])
        
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "PodChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": "pod-kill",
                "mode": mode,
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                }
            }
        }
        
        return self._apply_manifest(manifest, f"PodChaos/{name}")
    
    def create_pod_failure_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        duration: str = "30s"
    ) -> tuple[bool, str]:
        """
        Pod Failure Chaos 생성 (파드를 사용 불가능하게 만듦)
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택
            duration: 실험 지속 시간
            
        Returns:
            (성공 여부, 메시지)
        """
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "PodChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": "pod-failure",
                "mode": "one",
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                }
            }
        }
        
        return self._apply_manifest(manifest, f"PodChaos/{name}")
    
    def create_network_delay_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        latency: str = "100ms",
        duration: str = "30s"
    ) -> tuple[bool, str]:
        """
        Network Delay Chaos 생성
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택
            latency: 지연 시간 (예: "10ms", "100ms")
            duration: 실험 지속 시간
            
        Returns:
            (성공 여부, 메시지)
        """
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": "delay",
                "mode": "all",
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                },
                "delay": {
                    "latency": latency,
                    "correlation": "0",
                    "jitter": "0ms"
                }
            }
        }
        
        return self._apply_manifest(manifest, f"NetworkChaos/{name}")
    
    def create_network_loss_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        loss: str = "25",
        duration: str = "30s"
    ) -> tuple[bool, str]:
        """
        Network Packet Loss Chaos 생성
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택
            loss: 패킷 손실률 (0-100)
            duration: 실험 지속 시간
            
        Returns:
            (성공 여부, 메시지)
        """
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": "loss",
                "mode": "all",
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                },
                "loss": {
                    "loss": loss,
                    "correlation": "0"
                }
            }
        }
        
        return self._apply_manifest(manifest, f"NetworkChaos/{name}")
    
    def create_stress_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        memory: Optional[str] = None,
        cpu: Optional[str] = None,
        duration: str = "30s"
    ) -> tuple[bool, str]:
        """
        Stress Chaos 생성 (CPU/메모리 부하)
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택
            memory: 메모리 스트레스 (예: "256MB")
            cpu: CPU 스트레스 (예: "1" = 1 core)
            duration: 실험 지속 시간
            
        Returns:
            (성공 여부, 메시지)
        """
        stressors = {}
        if memory:
            stressors["memory"] = {"workers": 1, "size": memory}
        if cpu:
            stressors["cpu"] = {"workers": int(cpu), "load": 100}
        
        if not stressors:
            return False, "❌ memory 또는 cpu 중 하나는 지정해야 합니다"
        
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "mode": "all",
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                },
                "stressors": stressors
            }
        }
        
        return self._apply_manifest(manifest, f"StressChaos/{name}")
    
    def create_io_delay_chaos(
        self,
        name: str,
        label_selector: Dict[str, str],
        delay: str = "100ms",
        duration: str = "30s",
        path: str = "/",
        percent: int = 100
    ) -> tuple[bool, str]:
        """
        I/O Delay Chaos 생성
        
        Args:
            name: 실험 이름
            label_selector: 대상 파드 선택
            delay: I/O 지연 시간
            duration: 실험 지속 시간
            path: 대상 경로
            percent: 영향받는 I/O 작업 비율 (0-100)
            
        Returns:
            (성공 여부, 메시지)
        """
        manifest = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "IOChaos",
            "metadata": {
                "name": name,
                "namespace": self.namespace
            },
            "spec": {
                "action": "latency",
                "mode": "all",
                "duration": duration,
                "selector": {
                    "namespaces": [self.namespace],
                    "labelSelectors": label_selector
                },
                "volumePath": path,
                "path": path,
                "delay": delay,
                "percent": percent
            }
        }
        
        return self._apply_manifest(manifest, f"IOChaos/{name}")
    
    def delete_chaos(self, chaos_type: str, name: str) -> tuple[bool, str]:
        """
        Chaos 실험 삭제
        
        Args:
            chaos_type: PodChaos, NetworkChaos, StressChaos 등
            name: 실험 이름
            
        Returns:
            (성공 여부, 메시지)
        """
        success, result = run_kubectl([
            "delete", chaos_type, name,
            "-n", self.namespace,
            "--ignore-not-found"
        ])
        
        if success:
            return True, f"✅ {chaos_type}/{name} 삭제됨"
        return False, f"❌ {chaos_type}/{name} 삭제 실패: {result}"
    
    def list_chaos_experiments(self) -> List[Dict]:
        """
        실행 중인 Chaos 실험 목록 조회
        
        Returns:
            실험 목록
        """
        experiments = []
        
        # 각 타입별로 조회
        chaos_types = [
            "podchaos",
            "networkchaos",
            "stresschaos",
            "iochaos",
            "timechaos"
        ]
        
        for chaos_type in chaos_types:
            success, result = run_kubectl([
                "get", chaos_type,
                "-n", self.namespace,
                "-o", "json"
            ])
            
            if success and result:
                try:
                    data = json.loads(result)
                    for item in data.get("items", []):
                        experiments.append({
                            "type": chaos_type,
                            "name": item["metadata"]["name"],
                            "namespace": item["metadata"]["namespace"],
                            "created": item["metadata"].get("creationTimestamp"),
                            "spec": item.get("spec", {})
                        })
                except json.JSONDecodeError:
                    pass
        
        return experiments
    
    def get_chaos_status(self, chaos_type: str, name: str) -> Optional[Dict]:
        """
        특정 Chaos 실험의 상태 조회
        
        Args:
            chaos_type: PodChaos, NetworkChaos 등
            name: 실험 이름
            
        Returns:
            실험 상태 정보
        """
        success, result = run_kubectl([
            "get", chaos_type, name,
            "-n", self.namespace,
            "-o", "json"
        ])
        
        if success and result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _apply_manifest(self, manifest: Dict, resource_name: str) -> tuple[bool, str]:
        """
        Manifest를 클러스터에 적용
        
        Args:
            manifest: YAML 매니페스트 딕셔너리
            resource_name: 리소스 이름 (로깅용)
            
        Returns:
            (성공 여부, 메시지)
        """
        # JSON을 stdin으로 전달
        manifest_json = json.dumps(manifest)
        
        try:
            result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=manifest_json,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, f"✅ {resource_name} 생성됨\n{result.stdout}"
            else:
                return False, f"❌ {resource_name} 생성 실패\n{result.stderr}"
        
        except Exception as e:
            return False, f"❌ 오류 발생: {str(e)}"


def quick_pod_kill(
    namespace: str,
    label_selector: Dict[str, str],
    duration: str = "30s"
) -> tuple[bool, str]:
    """
    빠른 Pod Kill 실험
    
    Args:
        namespace: 네임스페이스
        label_selector: 파드 선택 라벨
        duration: 지속 시간
        
    Returns:
        (성공 여부, 메시지)
    """
    chaos = ChaosExperiment(namespace)
    name = f"quick-pod-kill-{label_selector.get('app', 'test')}"
    return chaos.create_pod_kill_chaos(name, label_selector, duration)


def quick_memory_stress(
    namespace: str,
    label_selector: Dict[str, str],
    memory: str = "256MB",
    duration: str = "1m"
) -> tuple[bool, str]:
    """
    빠른 메모리 스트레스 실험
    
    Args:
        namespace: 네임스페이스
        label_selector: 파드 선택 라벨
        memory: 메모리 크기
        duration: 지속 시간
        
    Returns:
        (성공 여부, 메시지)
    """
    chaos = ChaosExperiment(namespace)
    name = f"quick-memory-stress-{label_selector.get('app', 'test')}"
    return chaos.create_stress_chaos(name, label_selector, memory=memory, duration=duration)


def quick_network_delay(
    namespace: str,
    label_selector: Dict[str, str],
    latency: str = "100ms",
    duration: str = "30s"
) -> tuple[bool, str]:
    """
    빠른 네트워크 지연 실험
    
    Args:
        namespace: 네임스페이스
        label_selector: 파드 선택 라벨
        latency: 지연 시간
        duration: 지속 시간
        
    Returns:
        (성공 여부, 메시지)
    """
    chaos = ChaosExperiment(namespace)
    name = f"quick-network-delay-{label_selector.get('app', 'test')}"
    return chaos.create_network_delay_chaos(name, label_selector, latency, duration)
