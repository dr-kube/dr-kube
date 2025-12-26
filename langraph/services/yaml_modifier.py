"""YAML 파일 수정 유틸리티"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.utils.logger import get_logger

logger = get_logger(__name__)


class YamlModifier:
    """YAML 파일을 안전하게 수정하는 클래스"""
    
    def __init__(self, file_path: str, repo_root: str = "."):
        """
        Args:
            file_path: 수정할 YAML 파일 경로 (상대 경로)
            repo_root: 저장소 루트 경로
        """
        self.repo_root = Path(repo_root).resolve()
        self.file_path = self.repo_root / file_path
        self.original_content: Optional[str] = None
        self.data: Optional[Dict[str, Any]] = None
        
    def load(self) -> Dict[str, Any]:
        """YAML 파일 로드"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.file_path}")
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.original_content = f.read()
            self.data = yaml.safe_load(self.original_content) or {}
        
        logger.info(f"YAML 파일 로드 완료: {self.file_path}")
        return self.data
    
    def increase_memory_limit(self, memory_increase: str = "512Mi", path: Optional[str] = None) -> Dict[str, Any]:
        """
        메모리 리소스 제한 증가
        
        Args:
            memory_increase: 증가할 메모리 양 (예: "512Mi", "1Gi")
            path: resources가 있는 경로 (예: "resources", "imageRenderer.resources")
                  None이면 자동으로 찾음
                  
        Returns:
            변경된 데이터
        """
        if self.data is None:
            self.load()
        
        # resources 경로 찾기
        if path:
            resource_path = path.split(".")
        else:
            resource_path = self._find_resources_path()
        
        if not resource_path:
            logger.warning("resources 섹션을 찾을 수 없습니다. 기본 경로에 생성합니다.")
            resource_path = ["resources"]
        
        # 중첩된 딕셔너리 접근
        current = self.data
        for key in resource_path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # resources 섹션 생성/수정
        if resource_path[-1] not in current:
            current[resource_path[-1]] = {}
        
        resources = current[resource_path[-1]]
        
        # limits 설정
        if "limits" not in resources:
            resources["limits"] = {}
        
        current_memory = resources["limits"].get("memory", "256Mi")
        new_memory = self._add_memory(current_memory, memory_increase)
        resources["limits"]["memory"] = new_memory
        
        # requests도 함께 증가 (선택적)
        if "requests" not in resources:
            resources["requests"] = {}
        
        if "memory" not in resources["requests"]:
            resources["requests"]["memory"] = new_memory
        
        logger.info(f"메모리 제한 증가: {current_memory} -> {new_memory}")
        return self.data
    
    def _find_resources_path(self) -> Optional[list]:
        """resources 섹션 경로 자동 찾기"""
        if self.data is None:
            return None
        
        # 일반적인 경로들 시도
        common_paths = [
            ["resources"],
            ["imageRenderer", "resources"],
            ["initChownData", "resources"],
        ]
        
        for path in common_paths:
            current = self.data
            found = True
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    found = False
                    break
                current = current[key]
            
            if found and isinstance(current, dict):
                return path
        
        # 재귀적으로 찾기
        def find_recursive(obj, path=[]):
            if isinstance(obj, dict):
                if "resources" in obj and isinstance(obj["resources"], dict):
                    return path + ["resources"]
                for key, value in obj.items():
                    result = find_recursive(value, path + [key])
                    if result:
                        return result
            return None
        
        result = find_recursive(self.data)
        return result
    
    def _add_memory(self, current: str, increase: str) -> str:
        """메모리 값 더하기 (간단한 구현)"""
        # 숫자 추출
        def parse_memory(mem_str: str) -> tuple[float, str]:
            mem_str = mem_str.strip().upper()
            if mem_str.endswith("MI"):
                return float(mem_str[:-2]), "Mi"
            elif mem_str.endswith("GI"):
                return float(mem_str[:-2]), "Gi"
            elif mem_str.endswith("M"):
                return float(mem_str[:-1]), "Mi"
            elif mem_str.endswith("G"):
                return float(mem_str[:-1]), "Gi"
            else:
                # 기본값
                return float(mem_str) if mem_str.replace(".", "").isdigit() else 256.0, "Mi"
        
        current_val, current_unit = parse_memory(current)
        increase_val, increase_unit = parse_memory(increase)
        
        # 단위 통일 (Mi로)
        if increase_unit == "Gi":
            increase_val *= 1024
        if current_unit == "Gi":
            current_val *= 1024
            unit = "Gi"
        else:
            unit = "Mi"
        
        total = current_val + increase_val
        
        # Gi로 표현 가능하면 Gi 사용
        if total >= 1024 and unit == "Mi":
            return f"{total / 1024:.1f}Gi"
        else:
            return f"{int(total)}Mi"
    
    def get_content(self) -> str:
        """수정된 YAML 내용 반환"""
        if self.data is None:
            self.load()
        
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    def get_diff(self) -> str:
        """
        변경 사항을 git diff 형식으로 반환
        
        Returns:
            git diff 형식의 문자열
        """
        if self.data is None:
            self.load()
        
        if not self.original_content:
            return "원본 파일이 없습니다."
        
        original_lines = self.original_content.splitlines(keepends=True)
        new_content = self.get_content()
        new_lines = new_content.splitlines(keepends=True)
        
        # 간단한 diff 생성 (unified diff 형식)
        import difflib
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{self.file_path.name}",
            tofile=f"b/{self.file_path.name}",
            lineterm=""
        )
        
        return "".join(diff)
    
    def save(self, dry_run: bool = False) -> bool:
        """
        파일 저장
        
        Args:
            dry_run: True면 파일은 저장하되 [DRY-RUN] 로그만 남김 (실제 커밋은 안 함)
            
        Returns:
            저장 성공 여부
        """
        if self.data is None:
            self.load()
        
        content = self.get_content()
        
        # 백업 생성 (dry-run이어도 백업은 생성)
        backup_path = self.file_path.with_suffix(self.file_path.suffix + ".bak")
        if self.original_content:
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(self.original_content)
            if dry_run:
                logger.info(f"[DRY-RUN] 백업 생성: {backup_path}")
            else:
                logger.info(f"백업 생성: {backup_path}")
        
        # 파일 저장 (dry-run이어도 실제로 저장)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        if dry_run:
            logger.info(f"[DRY-RUN] 파일 저장 완료 (커밋은 안 함): {self.file_path}")
            logger.info(f"[DRY-RUN] 변경 내용 미리보기:\n{content[:500]}...")
        else:
            logger.info(f"파일 저장 완료: {self.file_path}")
        
        return True

