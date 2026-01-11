"""Git 클라이언트"""
import os
from typing import Optional, Dict, Any
import yaml
from git import Repo, GitCommandError

from src.tools.logger import get_logger

logger = get_logger(__name__)


class GitClient:
    """Git 저장소 클라이언트"""
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Git 클라이언트 초기화
        
        Args:
            repo_path: Git 저장소 경로 (없으면 환경 변수에서 로드)
        """
        self.repo_path = repo_path or os.getenv("GIT_REPO_PATH")
        if not self.repo_path:
            raise ValueError("GIT_REPO_PATH가 설정되지 않았습니다")
        
        if not os.path.exists(self.repo_path):
            raise ValueError(f"Git 저장소 경로가 존재하지 않습니다: {self.repo_path}")
        
        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Git 저장소 로드: {self.repo_path}")
        except Exception as e:
            logger.error(f"Git 저장소 로드 실패: {str(e)}")
            raise
    
    def get_values_yaml_structure(self, path: str = "values/values.yaml") -> str:
        """
        values.yaml 파일의 구조를 문자열로 반환
        
        Args:
            path: values.yaml 파일 경로 (저장소 루트 기준)
            
        Returns:
            YAML 구조 문자열
        """
        try:
            file_path = os.path.join(self.repo_path, path)
            if not os.path.exists(file_path):
                logger.warning(f"values.yaml 파일이 없습니다: {file_path}")
                return ""
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # YAML을 문자열로 변환 (주석 제거)
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"values.yaml 구조 읽기 실패: {str(e)}")
            return ""
    
    def update_values_yaml(
        self,
        changes: Dict[str, Any],
        path: str = "values/values.yaml"
    ) -> bool:
        """
        values.yaml 파일 업데이트
        
        Args:
            changes: 변경할 키-값 쌍 (중첩된 딕셔너리 지원)
            path: values.yaml 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            file_path = os.path.join(self.repo_path, path)
            if not os.path.exists(file_path):
                logger.error(f"values.yaml 파일이 없습니다: {file_path}")
                return False
            
            # YAML 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # 변경사항 적용
            self._apply_changes(data, changes)
            
            # YAML 파일 쓰기
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"values.yaml 업데이트 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"values.yaml 업데이트 실패: {str(e)}")
            return False
    
    def _apply_changes(self, data: Dict[str, Any], changes: Dict[str, Any]) -> None:
        """
        중첩된 딕셔너리에 변경사항 적용
        
        Args:
            data: 대상 딕셔너리
            changes: 변경사항
        """
        for key, value in changes.items():
            if isinstance(value, dict) and key in data and isinstance(data[key], dict):
                self._apply_changes(data[key], value)
            else:
                data[key] = value
    
    def commit_changes(
        self,
        message: str,
        branch: str = "main"
    ) -> bool:
        """
        변경사항 커밋 (Phase 1: 시뮬레이션)
        
        Args:
            message: 커밋 메시지
            branch: 브랜치 이름
            
        Returns:
            성공 여부
        """
        try:
            # Phase 1: 실제 커밋은 하지 않고 시뮬레이션만
            logger.info(f"[시뮬레이션] 커밋 메시지: {message}")
            logger.info(f"[시뮬레이션] 브랜치: {branch}")
            
            # 실제 커밋을 원하는 경우 아래 주석 해제
            # self.repo.git.add(A=True)
            # self.repo.index.commit(message)
            # logger.info(f"변경사항 커밋 완료: {message}")
            
            return True
            
        except GitCommandError as e:
            logger.error(f"Git 커밋 실패: {str(e)}")
            return False
    
    def push_changes(self, branch: str = "main") -> bool:
        """
        변경사항 푸시 (Phase 1: 시뮬레이션)
        
        Args:
            branch: 브랜치 이름
            
        Returns:
            성공 여부
        """
        try:
            # Phase 1: 실제 푸시는 하지 않고 시뮬레이션만
            logger.info(f"[시뮬레이션] 푸시 브랜치: {branch}")
            
            # 실제 푸시를 원하는 경우 아래 주석 해제
            # origin = self.repo.remote(name='origin')
            # origin.push(branch)
            # logger.info(f"변경사항 푸시 완료: {branch}")
            
            return True
            
        except GitCommandError as e:
            logger.error(f"Git 푸시 실패: {str(e)}")
            return False
