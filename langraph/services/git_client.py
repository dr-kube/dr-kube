"""Git 작업 클라이언트"""
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.utils.logger import get_logger

logger = get_logger(__name__)


class GitClient:
    """Git 작업을 수행하는 클라이언트"""
    
    def __init__(self, repo_path: str = "."):
        """
        Args:
            repo_path: Git 저장소 경로
        """
        self.repo_path = Path(repo_path).resolve()
        if not (self.repo_path / ".git").exists():
            logger.warning(f"Git 저장소가 아닙니다: {self.repo_path}")
    
    def _run_git(self, args: List[str], dry_run: bool = False) -> tuple[int, str, str]:
        """Git 명령 실행"""
        if dry_run:
            logger.info(f"[DRY-RUN] git {' '.join(args)}")
            return 0, "", ""
        
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            logger.error("Git이 설치되어 있지 않습니다")
            return 1, "", "Git not found"
    
    def status(self) -> Dict[str, List[str]]:
        """변경된 파일 목록 반환"""
        returncode, stdout, stderr = self._run_git(["status", "--porcelain"])
        
        if returncode != 0:
            logger.error(f"Git status 실패: {stderr}")
            return {"modified": [], "untracked": []}
        
        modified = []
        untracked = []
        
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            filename = line[3:]
            
            if status.startswith("??"):
                untracked.append(filename)
            else:
                modified.append(filename)
        
        return {"modified": modified, "untracked": untracked}
    
    def add(self, files: List[str], dry_run: bool = False) -> bool:
        """파일을 staging area에 추가"""
        if not files:
            return True
        
        returncode, stdout, stderr = self._run_git(["add"] + files, dry_run)
        
        if returncode == 0:
            logger.info(f"파일 추가 완료: {files}")
            return True
        else:
            logger.error(f"파일 추가 실패: {stderr}")
            return False
    
    def commit(self, message: str, dry_run: bool = False) -> Optional[str]:
        """
        변경사항 커밋
        
        Args:
            message: 커밋 메시지
            dry_run: True면 실제로 커밋하지 않음
            
        Returns:
            커밋 해시 또는 None
        """
        if dry_run:
            logger.info(f"[DRY-RUN] 커밋 메시지: {message}")
            return "dry-run-commit-hash"
        
        returncode, stdout, stderr = self._run_git(
            ["commit", "-m", message],
            dry_run
        )
        
        if returncode == 0:
            # 커밋 해시 가져오기
            returncode, commit_hash, _ = self._run_git(["rev-parse", "HEAD"])
            if returncode == 0:
                commit_hash = commit_hash.strip()
                logger.info(f"커밋 완료: {commit_hash}")
                return commit_hash
        
        logger.error(f"커밋 실패: {stderr}")
        return None
    
    def push(self, remote: str = "origin", branch: str = "main", dry_run: bool = False) -> bool:
        """원격 저장소에 푸시"""
        if dry_run:
            logger.info(f"[DRY-RUN] git push {remote} {branch}")
            return True
        
        returncode, stdout, stderr = self._run_git(
            ["push", remote, branch],
            dry_run
        )
        
        if returncode == 0:
            logger.info(f"푸시 완료: {remote}/{branch}")
            return True
        
        logger.error(f"푸시 실패: {stderr}")
        return False

