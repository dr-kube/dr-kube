"""
Git 액션 생성 및 커밋 모듈
근본 원인 분석 결과를 바탕으로 Git 변경사항을 생성하고 커밋합니다.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from dataclasses import dataclass


@dataclass
class GitAction:
    """Git 액션 정보"""
    action_type: str  # create, modify, delete
    file_path: str
    content: Optional[str] = None
    description: str = ""


class GitActionGenerator:
    """Git 액션 생성 클래스"""
    
    def __init__(self, repo_path: str = ".", simulate: bool = True):
        """
        초기화
        
        Args:
            repo_path: Git 저장소 경로 (기본값: 현재 디렉토리)
            simulate: 시뮬레이션 모드 여부 (기본값: True)
        """
        self.repo_path = Path(repo_path).resolve()
        self.simulate = simulate
        logger.info(f"GitActionGenerator 초기화 (저장소: {self.repo_path}, 시뮬레이션: {simulate})")
    
    def generate_actions_from_analysis(self, analyses: List[Any], 
                                       error_summary: Dict[str, Any],
                                       pod_metadata: Optional[Any] = None,
                                       resource_types: Optional[List[str]] = None) -> List[GitAction]:
        """
        근본 원인 분석 결과로부터 Git 액션 생성
        
        Args:
            analyses: RootCauseAnalysis 객체 리스트
            error_summary: 에러 요약 정보
            pod_metadata: Pod/서비스 메타데이터 (선택사항)
            resource_types: 선택된 리소스 타입 리스트 (선택사항, 기본값: ["all"])
            
        Returns:
            GitAction 객체 리스트
        """
        if resource_types is None:
            resource_types = ["all"]
        
        actions = []
        
        for analysis in analyses:
            # 각 분석 결과에 대해 적절한 액션 생성
            category_actions = self._generate_actions_for_category(
                analysis, error_summary, pod_metadata, resource_types
            )
            actions.extend(category_actions)
        
        logger.info(f"총 {len(actions)}개의 Git 액션 생성됨 (리소스 타입: {', '.join(resource_types)})")
        return actions
    
    def _generate_actions_for_category(self, analysis: Any, 
                                      error_summary: Dict[str, Any],
                                      pod_metadata: Optional[Any] = None,
                                      resource_types: Optional[List[str]] = None) -> List[GitAction]:
        """
        특정 카테고리에 대한 Git 액션 생성
        
        Args:
            analysis: RootCauseAnalysis 객체
            error_summary: 에러 요약 정보
            pod_metadata: Pod/서비스 메타데이터
            resource_types: 선택된 리소스 타입 리스트
            
        Returns:
            GitAction 객체 리스트
        """
        if resource_types is None:
            resource_types = ["all"]
        
        actions = []
        category = analysis.category
        
        # 리소스 타입 필터링: "all"이면 모든 리소스 타입, 아니면 선택한 것만
        should_create_patch = "all" in resource_types
        
        # 카테고리별 액션 생성 로직
        if "리소스 부족" in category:
            # 리소스 부족 시 Kubernetes 리소스 조정 파일 생성
            if should_create_patch or "pod" in resource_types or "deployment" in resource_types or "resourcequota" in resource_types:
                actions.append(self._create_resource_patch_action(analysis, resource_types))
        
        elif "네트워크 오류" in category:
            # 네트워크 오류 시 네트워크 정책 또는 서비스 설정 파일 생성
            if should_create_patch or "service" in resource_types or "networkpolicy" in resource_types:
                actions.append(self._create_network_config_action(analysis, resource_types))
        
        elif "컨테이너/Kubernetes 오류" in category:
            # Kubernetes 오류 시 Deployment/Pod 설정 파일 생성
            if should_create_patch or "pod" in resource_types or "deployment" in resource_types:
                actions.append(self._create_k8s_config_action(analysis, resource_types))
        
        elif "설정 오류" in category:
            # 설정 오류 시 설정 파일 수정
            if should_create_patch or "configmap" in resource_types or "secret" in resource_types:
                actions.append(self._create_config_fix_action(analysis, resource_types))
        
        # 모든 카테고리에 대해 분석 리포트 생성 (리소스 타입 정보 포함)
        actions.append(self._create_analysis_report_action(analysis, error_summary, pod_metadata, resource_types))
        
        return actions
    
    def _create_resource_patch_action(self, analysis: Any, resource_types: Optional[List[str]] = None) -> GitAction:
        """리소스 부족 문제에 대한 패치 액션 생성"""
        # 예시: 리소스 제한 증가를 위한 패치 파일
        patch_content = f"""# 리소스 부족 문제 해결을 위한 리소스 조정
# 생성일: {self._get_timestamp()}
# 카테고리: {analysis.category}
# 근본 원인: {analysis.root_cause}

# 리소스 제한을 증가시키는 예시
# 실제 적용 시에는 적절한 값으로 수정하세요
apiVersion: v1
kind: ResourceQuota
metadata:
  name: increased-resources
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
"""
        
        file_path = f"patches/resource-patch-{self._sanitize_category(analysis.category)}.yaml"
        return GitAction(
            action_type="create",
            file_path=file_path,
            content=patch_content,
            description=f"{analysis.category} 해결을 위한 리소스 패치"
        )
    
    def _create_network_config_action(self, analysis: Any, resource_types: Optional[List[str]] = None) -> GitAction:
        """네트워크 오류에 대한 설정 액션 생성"""
        config_content = f"""# 네트워크 오류 해결을 위한 설정
# 생성일: {self._get_timestamp()}
# 카테고리: {analysis.category}
# 근본 원인: {analysis.root_cause}

# 네트워크 정책 또는 서비스 설정 예시
# 실제 적용 시에는 적절한 값으로 수정하세요
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: network-fix
spec:
  podSelector: {{}}
  policyTypes:
  - Ingress
  - Egress
"""
        
        file_path = f"patches/network-config-{self._sanitize_category(analysis.category)}.yaml"
        return GitAction(
            action_type="create",
            file_path=file_path,
            content=config_content,
            description=f"{analysis.category} 해결을 위한 네트워크 설정"
        )
    
    def _create_k8s_config_action(self, analysis: Any, resource_types: Optional[List[str]] = None) -> GitAction:
        """Kubernetes 오류에 대한 설정 액션 생성"""
        config_content = f"""# Kubernetes 오류 해결을 위한 설정
# 생성일: {self._get_timestamp()}
# 카테고리: {analysis.category}
# 근본 원인: {analysis.root_cause}

# Deployment 또는 Pod 설정 예시
# 실제 적용 시에는 적절한 값으로 수정하세요
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fixed-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fixed-app
  template:
    metadata:
      labels:
        app: fixed-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
"""
        
        file_path = f"patches/k8s-config-{self._sanitize_category(analysis.category)}.yaml"
        return GitAction(
            action_type="create",
            file_path=file_path,
            content=config_content,
            description=f"{analysis.category} 해결을 위한 Kubernetes 설정"
        )
    
    def _create_config_fix_action(self, analysis: Any, resource_types: Optional[List[str]] = None) -> GitAction:
        """설정 오류에 대한 수정 액션 생성"""
        fix_content = f"""# 설정 오류 수정
# 생성일: {self._get_timestamp()}
# 카테고리: {analysis.category}
# 근본 원인: {analysis.root_cause}

# 설정 파일 수정 사항:
# {chr(10).join(f'- {action}' for action in analysis.suggested_actions)}
"""
        
        file_path = f"patches/config-fix-{self._sanitize_category(analysis.category)}.md"
        return GitAction(
            action_type="create",
            file_path=file_path,
            content=fix_content,
            description=f"{analysis.category} 해결을 위한 설정 수정"
        )
    
    def _create_analysis_report_action(self, analysis: Any, 
                                      error_summary: Dict[str, Any],
                                      pod_metadata: Optional[Any] = None,
                                      resource_types: Optional[List[str]] = None) -> GitAction:
        """분석 리포트 액션 생성"""
        
        # Pod/서비스 정보 섹션 생성
        pod_info_section = ""
        if pod_metadata:
            if isinstance(pod_metadata, list):
                # 여러 Pod인 경우
                pod_info_section = "### 영향받는 Pod/서비스\n\n"
                for idx, pod_info in enumerate(pod_metadata, 1):
                    pod_info_section += f"#### Pod {idx}\n\n"
                    pod_info_section += f"- **Pod 이름**: `{pod_info.get('pod_name', 'N/A')}`\n"
                    pod_info_section += f"- **네임스페이스**: `{pod_info.get('namespace', 'N/A')}`\n"
                    if pod_info.get('service_name'):
                        pod_info_section += f"- **서비스 이름**: `{pod_info.get('service_name')}`\n"
                    if pod_info.get('node_name'):
                        pod_info_section += f"- **노드**: `{pod_info.get('node_name')}`\n"
                    if pod_info.get('phase'):
                        pod_info_section += f"- **상태**: `{pod_info.get('phase')}`\n"
                    if pod_info.get('containers'):
                        pod_info_section += f"- **컨테이너**: {', '.join(pod_info.get('containers', []))}\n"
                    pod_info_section += "\n"
            else:
                # 단일 Pod인 경우
                pod_info_section = "### 영향받는 Pod/서비스\n\n"
                pod_info_section += f"- **Pod 이름**: `{pod_metadata.get('pod_name', 'N/A')}`\n"
                pod_info_section += f"- **네임스페이스**: `{pod_metadata.get('namespace', 'N/A')}`\n"
                if pod_metadata.get('service_name'):
                    pod_info_section += f"- **서비스 이름**: `{pod_metadata.get('service_name')}`\n"
                if pod_metadata.get('node_name'):
                    pod_info_section += f"- **노드**: `{pod_metadata.get('node_name')}`\n"
                if pod_metadata.get('phase'):
                    pod_info_section += f"- **상태**: `{pod_metadata.get('phase')}`\n"
                if pod_metadata.get('containers'):
                    pod_info_section += f"- **컨테이너**: {', '.join(pod_metadata.get('containers', []))}\n"
                pod_info_section += "\n"
        
        # 리소스 타입 정보 섹션 생성
        resource_type_section = ""
        if resource_types and resource_types != ["all"]:
            resource_type_names = {
                "pod": "Pod",
                "service": "Service",
                "deployment": "Deployment",
                "configmap": "ConfigMap",
                "secret": "Secret",
                "pv": "PersistentVolume",
                "pvc": "PersistentVolumeClaim",
                "networkpolicy": "NetworkPolicy",
                "resourcequota": "ResourceQuota",
                "limitrange": "LimitRange"
            }
            selected_names = [resource_type_names.get(rt, rt) for rt in resource_types if rt != "all"]
            if selected_names:
                resource_type_section = f"### 대상 리소스 타입\n\n"
                resource_type_section += ", ".join(f"`{name}`" for name in selected_names)
                resource_type_section += "\n\n"
        
        # 장애 등급 정보 생성
        severity = getattr(analysis, 'severity', 'medium')
        severity_info = {
            "critical": {"icon": "🔴", "name": "치명적", "description": "즉시 조치 필요 - 서비스 중단 또는 데이터 손실 위험"},
            "high": {"icon": "🟠", "name": "높음", "description": "빠른 조치 권장 - 서비스 성능 저하 또는 일부 기능 불가"},
            "medium": {"icon": "🟡", "name": "보통", "description": "조치 필요 - 일시적 문제 또는 제한적 영향"},
            "low": {"icon": "🟢", "name": "낮음", "description": "모니터링 권장 - 경미한 문제 또는 자동 복구 가능"}
        }
        severity_detail = severity_info.get(severity, severity_info["medium"])
        
        severity_section = f"""### 장애 등급

{severity_detail['icon']} **{severity_detail['name']}** ({severity.upper()})

{severity_detail['description']}

"""
        
        report_content = f"""# 에러 분석 리포트

## 카테고리: {analysis.category}

{severity_section}{pod_info_section}{resource_type_section}### 근본 원인
{analysis.root_cause}

### 상세 설명
{analysis.explanation}

### 권장 조치사항
{chr(10).join(f'{i+1}. {action}' for i, action in enumerate(analysis.suggested_actions))}

### 신뢰도
{analysis.confidence:.2%}

### 에러 요약
- 총 에러 수: {error_summary.get('total_errors', 0)}
- 심각도 분포: {error_summary.get('severity_counts', {})}

---
생성일: {self._get_timestamp()}
"""
        
        file_path = f"reports/analysis-{self._sanitize_category(analysis.category)}.md"
        return GitAction(
            action_type="create",
            file_path=file_path,
            content=report_content,
            description=f"{analysis.category} 분석 리포트"
        )
    
    def apply_actions(self, actions: List[GitAction]) -> bool:
        """
        Git 액션 적용
        
        Args:
            actions: GitAction 객체 리스트
            
        Returns:
            성공 여부
        """
        try:
            # patches 및 reports 디렉토리 생성
            patches_dir = self.repo_path / "patches"
            reports_dir = self.repo_path / "reports"
            patches_dir.mkdir(exist_ok=True)
            reports_dir.mkdir(exist_ok=True)
            
            if self.simulate:
                logger.info("=== 시뮬레이션 모드: 파일은 생성하지만 Git 커밋은 하지 않음 ===")
            
            # 각 액션 적용
            for action in actions:
                file_path = self.repo_path / action.file_path
                
                if action.action_type == "create":
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(action.content)
                    if self.simulate:
                        logger.info(f"[시뮬레이션] 파일 생성: {action.file_path}")
                    else:
                        logger.info(f"파일 생성: {action.file_path}")
                
                elif action.action_type == "modify":
                    if file_path.exists():
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(action.content)
                        if self.simulate:
                            logger.info(f"[시뮬레이션] 파일 수정: {action.file_path}")
                        else:
                            logger.info(f"파일 수정: {action.file_path}")
                    else:
                        logger.warning(f"수정할 파일이 없습니다: {action.file_path}")
                
                elif action.action_type == "delete":
                    if file_path.exists():
                        file_path.unlink()
                        if self.simulate:
                            logger.info(f"[시뮬레이션] 파일 삭제: {action.file_path}")
                        else:
                            logger.info(f"파일 삭제: {action.file_path}")
                    else:
                        logger.warning(f"삭제할 파일이 없습니다: {action.file_path}")
            
            if self.simulate:
                logger.info("=== 시뮬레이션 모드: 파일은 생성되었지만 Git 커밋은 수행하지 않습니다 ===")
            
            return True
        
        except Exception as e:
            logger.error(f"Git 액션 적용 중 오류: {e}")
            return False
    
    def commit_changes(self, commit_message: str, branch: str = "main") -> bool:
        """
        변경사항 커밋 (시뮬레이션 모드에서는 실제 커밋하지 않음)
        
        Args:
            commit_message: 커밋 메시지
            branch: 브랜치 이름
            
        Returns:
            성공 여부
        """
        if self.simulate:
            logger.info(f"=== 시뮬레이션: 커밋 메시지 ===")
            logger.info(f"브랜치: {branch}")
            logger.info(f"메시지: {commit_message}")
            return True
        
        try:
            # Git 명령 실행
            os.chdir(self.repo_path)
            
            # 변경사항 확인
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                logger.info("커밋할 변경사항이 없습니다")
                return True
            
            # 변경사항 추가
            subprocess.run(
                ["git", "add", "."],
                check=True
            )
            
            # 커밋
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True
            )
            
            logger.info(f"커밋 완료: {commit_message}")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Git 커밋 중 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"커밋 중 예상치 못한 오류: {e}")
            return False
    
    def _sanitize_category(self, category: str) -> str:
        """카테고리 이름을 파일명으로 사용 가능한 형태로 변환"""
        return category.replace(" ", "-").replace("/", "-").lower()
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프 문자열 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

