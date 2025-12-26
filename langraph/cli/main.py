"""CLI 진입점"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.agents.graph import create_incident_response_graph
from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """메인 CLI 함수"""
    parser = argparse.ArgumentParser(
        description="DevOps 장애 대응 자동화 LangGraph 시스템"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="분석할 로그 파일 경로"
    )
    parser.add_argument(
        "--log-text",
        type=str,
        help="직접 입력할 로그 텍스트"
    )
    parser.add_argument(
        "--log-source",
        type=str,
        default="file",
        help="로그 소스 (file, loki, prometheus)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run 모드 (실제 파일 수정 및 커밋 안 함)"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default="../..",
        help="Git 저장소 루트 경로 (기본값: 상위 2단계, dr-kube 디렉토리의 상위)"
    )
    
    args = parser.parse_args()
    
    # 로그 입력 확인
    if not args.log_file and not args.log_text:
        parser.error("--log-file 또는 --log-text 중 하나는 필수입니다")
    
    # repo_root 경로 해석 (스크립트 위치 기준)
    script_dir = Path(__file__).parent.parent  # langraph 디렉토리
    if Path(args.repo_root).is_absolute():
        repo_root = args.repo_root
    else:
        # 상대 경로는 스크립트 위치 기준으로 해석
        repo_root = str((script_dir / args.repo_root).resolve())
    
    logger.info(f"Repo root 경로: {repo_root}")
    
    # 초기 State 생성
    initial_state: IncidentState = {
        "raw_log": args.log_text or "",
        "log_source": args.log_source,
        "log_file_path": args.log_file,
        "affected_apps": [],
        "git_changes": {},
        "incident_id": "",
        "workflow_status": "initialized",
        "user_feedback_history": [],
        "created_at": "",
        "updated_at": "",
        "dry_run": args.dry_run,
        "repo_root": repo_root,
        "modified_files": [],
    }
    
    # 그래프 생성 및 실행
    logger.info("워크플로우 시작")
    graph = create_incident_response_graph()
    
    try:
        final_state = graph.invoke(initial_state)
        logger.info("워크플로우 완료")
        return 0
    except Exception as e:
        logger.error(f"워크플로우 실행 중 오류 발생: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

