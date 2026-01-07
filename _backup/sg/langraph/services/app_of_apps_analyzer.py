"""App of Apps 구조 분석기"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.utils.logger import get_logger

logger = get_logger(__name__)


class AppOfAppsAnalyzer:
    """App of Apps 구조를 분석하여 애플리케이션과 values.yaml 파일을 매핑"""
    
    def __init__(self, repo_root: str = "."):
        """
        Args:
            repo_root: Git 저장소 루트 경로
        """
        self.repo_root = Path(repo_root).resolve()
        self.apps_map: Dict[str, Dict] = {}
        
    def analyze(self) -> Dict[str, Dict]:
        """
        App of Apps 구조를 분석하여 앱 이름과 values.yaml 경로를 매핑
        
        Returns:
            {app_name: {values_path: str, application_path: str}}
        """
        logger.info(f"App of Apps 구조 분석 시작: {self.repo_root}")
        
        # dr-kube 디렉토리 찾기 (여러 경로 시도)
        apps_dir = None
        
        # 1. repo_root가 이미 dr-kube 디렉토리인지 확인
        if self.repo_root.name == "dr-kube" and (self.repo_root / "grafana" / "Application.yaml").exists():
            apps_dir = self.repo_root
            logger.info(f"경로 1 성공: repo_root가 dr-kube 디렉토리")
        # 2. repo_root/dr-kube 경로 시도
        elif (self.repo_root / "dr-kube").exists() and (self.repo_root / "dr-kube" / "grafana" / "Application.yaml").exists():
            apps_dir = self.repo_root / "dr-kube"
            logger.info(f"경로 2 성공: repo_root/dr-kube")
        # 3. repo_root에서 위로 올라가면서 dr-kube 찾기
        else:
            current = self.repo_root
            for _ in range(5):  # 최대 5단계 위로
                if current.name == "dr-kube" and (current / "grafana" / "Application.yaml").exists():
                    apps_dir = current
                    logger.info(f"경로 3 성공: {current}")
                    break
                if (current / "dr-kube").exists() and (current / "dr-kube" / "grafana" / "Application.yaml").exists():
                    apps_dir = current / "dr-kube"
                    logger.info(f"경로 4 성공: {current / 'dr-kube'}")
                    break
                if current.parent == current:  # 루트에 도달
                    break
                current = current.parent
        
        if not apps_dir:
            logger.warning(f"dr-kube 디렉토리를 찾을 수 없습니다. 시도한 경로:")
            logger.warning(f"  1. {self.repo_root} (이름이 dr-kube인지 확인)")
            logger.warning(f"  2. {self.repo_root / 'dr-kube'}")
            logger.warning(f"  3. {self.repo_root.parent} 및 상위 디렉토리들")
            return {}
        
        logger.info(f"앱 디렉토리: {apps_dir}")
        
        # 각 앱 디렉토리 스캔
        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue
                
            app_name = app_dir.name
            application_file = app_dir / "Application.yaml"
            
            if not application_file.exists():
                continue
            
            # Application.yaml 파싱하여 values.yaml 경로 찾기
            try:
                with open(application_file, "r", encoding="utf-8") as f:
                    app_config = yaml.safe_load(f)
                
                values_path = self._extract_values_path(app_config, app_name, apps_dir)
                
                if values_path:
                    # application_path는 repo_root 기준으로 계산
                    try:
                        app_path = application_file.relative_to(self.repo_root)
                    except ValueError:
                        # repo_root가 apps_dir의 상위가 아닌 경우
                        app_path = application_file.relative_to(apps_dir.parent) if apps_dir != self.repo_root else application_file.relative_to(self.repo_root)
                    
                    self.apps_map[app_name] = {
                        "values_path": str(values_path),
                        "application_path": str(app_path),
                        "namespace": app_config.get("spec", {}).get("destination", {}).get("namespace", "default"),
                    }
                    logger.info(f"앱 발견: {app_name} -> {values_path}")
                    
            except Exception as e:
                logger.warning(f"Application.yaml 파싱 실패 ({app_name}): {e}")
        
        logger.info(f"총 {len(self.apps_map)}개 앱 발견")
        return self.apps_map
    
    def _extract_values_path(self, app_config: dict, app_name: str, apps_dir: Path) -> Optional[Path]:
        """Application.yaml에서 values.yaml 경로 추출"""
        sources = app_config.get("spec", {}).get("sources", [])
        
        for source in sources:
            helm_config = source.get("helm", {})
            value_files = helm_config.get("valueFiles", [])
            
            for value_file in value_files:
                # $values/helm-values/{app}/values.yaml 형식
                if value_file.startswith("$values/helm-values/"):
                    # $values 제거하고 실제 경로로 변환
                    relative_path = value_file.replace("$values/", "")
                    full_path = apps_dir / relative_path
                    
                    if full_path.exists():
                        try:
                            return full_path.relative_to(self.repo_root)
                        except ValueError:
                            # repo_root 기준으로 계산 불가능한 경우 절대 경로 사용
                            return full_path
        
        # 기본 경로 시도
        default_path = apps_dir / "helm-values" / app_name / "values.yaml"
        if default_path.exists():
            try:
                return default_path.relative_to(self.repo_root)
            except ValueError:
                return default_path
        
        return None
    
    def get_values_path(self, app_name: str) -> Optional[str]:
        """앱 이름으로 values.yaml 경로 반환"""
        if not self.apps_map:
            self.analyze()
        
        app_info = self.apps_map.get(app_name)
        if app_info:
            return app_info["values_path"]
        return None
    
    def find_app_by_pod_name(self, pod_name: str) -> Optional[str]:
        """
        Pod 이름으로 앱 이름 찾기 (예: grafana-xxx -> grafana)
        
        Args:
            pod_name: Pod 이름
            
        Returns:
            앱 이름 또는 None
        """
        # Pod 이름에서 앱 이름 추출 (예: grafana-7d8f9c4b5-xk2m3 -> grafana)
        app_name = pod_name.split("-")[0]
        
        if not self.apps_map:
            self.analyze()
        
        if app_name in self.apps_map:
            return app_name
        
        # 부분 매칭 시도
        for known_app in self.apps_map.keys():
            if known_app.startswith(app_name) or app_name.startswith(known_app):
                return known_app
        
        return None

