"""GitHub 클라이언트 - PR 생성"""
import os
import subprocess
from pathlib import Path
from datetime import datetime


class GitHubClient:
    """GitHub PR 생성 클라이언트"""

    def __init__(self, repo_path: str = None):
        """
        Args:
            repo_path: Git 저장소 경로 (기본: 프로젝트 루트)
        """
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            # agent/dr_kube/github.py -> 프로젝트 루트
            self.repo_path = Path(__file__).parent.parent.parent.parent

    def _run_git(self, *args) -> tuple[bool, str]:
        """Git 명령어 실행"""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()

    def create_branch(self, branch_name: str) -> tuple[bool, str]:
        """새 브랜치 생성 및 체크아웃"""
        # 먼저 main으로 이동
        self._run_git("checkout", "main")
        self._run_git("pull", "origin", "main")

        # 브랜치 생성
        success, msg = self._run_git("checkout", "-b", branch_name)
        if not success:
            # 이미 존재하면 체크아웃만
            success, msg = self._run_git("checkout", branch_name)
        return success, msg

    def commit_and_push(
        self, file_path: str, commit_message: str, branch_name: str
    ) -> tuple[bool, str]:
        """파일 커밋 및 푸시"""
        # 파일 추가
        success, msg = self._run_git("add", file_path)
        if not success:
            return False, f"git add 실패: {msg}"

        # 커밋
        success, msg = self._run_git("commit", "-m", commit_message)
        if not success:
            return False, f"git commit 실패: {msg}"

        # 푸시
        success, msg = self._run_git("push", "-u", "origin", branch_name)
        if not success:
            return False, f"git push 실패: {msg}"

        return True, "커밋 및 푸시 완료"

    def create_pr(
        self, branch_name: str, title: str, body: str
    ) -> tuple[bool, str, int]:
        """GitHub PR 생성 (gh CLI 사용)"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "main",
                    "--head",
                    branch_name,
                    "--title",
                    title,
                    "--body",
                    body,
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            pr_url = result.stdout.strip()
            # URL에서 PR 번호 추출
            pr_number = int(pr_url.split("/")[-1])
            return True, pr_url, pr_number
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip(), 0
        except FileNotFoundError:
            return False, "gh CLI가 설치되어 있지 않습니다. brew install gh", 0

    def cleanup(self) -> None:
        """main 브랜치로 복귀"""
        self._run_git("checkout", "main")


def generate_branch_name(issue_type: str, resource: str) -> str:
    """브랜치명 생성"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # 리소스명에서 안전한 문자만 추출
    safe_resource = "".join(c for c in resource if c.isalnum() or c == "-")[:20]
    return f"fix/{issue_type}-{safe_resource}-{timestamp}"


def generate_pr_body(state: dict) -> str:
    """PR 본문 생성"""
    return f"""## 🔧 DR-Kube 자동 수정

### 이슈 정보
- **타입**: {state.get('issue_data', {}).get('type', 'unknown')}
- **리소스**: {state.get('issue_data', {}).get('resource', 'unknown')}
- **네임스페이스**: {state.get('issue_data', {}).get('namespace', 'default')}
- **심각도**: {state.get('severity', 'medium')}

### 근본 원인
{state.get('root_cause', 'N/A')}

### 변경 내용
{state.get('fix_description', 'N/A')}

### 수정된 파일
- `{state.get('target_file', 'N/A')}`

---
> 이 PR은 DR-Kube 에이전트에 의해 자동 생성되었습니다.
"""
