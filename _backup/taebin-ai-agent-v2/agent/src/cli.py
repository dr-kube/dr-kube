"""CLI 인터페이스"""
import argparse
import json
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from src.dr_kube.graph import create_graph
from src.dr_kube.state import AgentState
from src.tools.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


def load_logs_from_file(file_path: str) -> list[str]:
    """
    로컬 파일에서 로그 읽기
    
    Args:
        file_path: 로그 파일 경로
        
    Returns:
        로그 리스트
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            logs = [line.strip() for line in f if line.strip()]
        logger.info(f"로그 파일 로드: {file_path} ({len(logs)}개 로그)")
        return logs
    except Exception as e:
        logger.error(f"로그 파일 로드 실패: {str(e)}")
        raise


def main():
    """메인 CLI 함수"""
    parser = argparse.ArgumentParser(
        description="Kubernetes 장애 분석 및 자동 복구 AI Agent"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="로컬 로그 파일 경로"
    )
    
    parser.add_argument(
        "--loki",
        action="store_true",
        help="Loki에서 로그 수집"
    )
    
    parser.add_argument(
        "--namespace",
        type=str,
        default="default",
        help="Kubernetes 네임스페이스"
    )
    
    parser.add_argument(
        "--all-namespaces",
        action="store_true",
        help="모든 네임스페이스에서 조회 (--namespace 옵션 무시)"
    )
    
    parser.add_argument(
        "--resource-type",
        type=str,
        help="리소스 타입 (Pod, Deployment 등)"
    )
    
    parser.add_argument(
        "--resource-name",
        type=str,
        help="리소스 이름"
    )
    
    parser.add_argument(
        "--git-repo-path",
        type=str,
        help="Git 저장소 경로 (없으면 환경 변수에서 로드)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="시뮬레이션 모드 (실제 Git 커밋/푸시 안 함)"
    )
    
    args = parser.parse_args()
    
    # 초기 상태 설정
    initial_state: AgentState = {
        "logs": [],
        "log_source": "file",
        "error_category": None,
        "error_type": None,
        "root_cause": None,
        "severity": None,
        "analysis": None,
        "suggested_actions": [],
        "git_changes": None,
        "recovery_status": None,
        "user_feedback": None,
        "user_approved": True,  # Phase 1: 자동 승인
        "namespace": None if args.all_namespaces else args.namespace,
        "all_namespaces": args.all_namespaces,
        "resource_name": args.resource_name,
        "resource_type": args.resource_type,
        "error": None,
        "status": "pending"
    }
    
    # 로그 수집
    if args.log_file:
        initial_state["logs"] = load_logs_from_file(args.log_file)
        initial_state["log_source"] = "file"
    elif args.loki:
        initial_state["log_source"] = "loki"
        # TODO: Loki에서 로그 수집 구현
        logger.info("Loki에서 로그 수집 (구현 예정)")
    else:
        logger.error("로그 소스를 지정해주세요 (--log-file 또는 --loki)")
        return
    
    # Git 저장소 경로 설정
    if args.git_repo_path:
        initial_state["git_repo_path"] = args.git_repo_path
    elif os.getenv("GIT_REPO_PATH"):
        initial_state["git_repo_path"] = os.getenv("GIT_REPO_PATH")
    
    # 워크플로우 실행
    try:
        logger.info("워크플로우 시작")
        graph = create_graph()
        result = graph.invoke(initial_state)
        
        # 결과 출력
        print("\n=== 워크플로우 실행 결과 ===")
        print(f"상태: {result.get('status')}")
        print(f"에러 카테고리: {result.get('error_category')}")
        print(f"근본 원인: {result.get('root_cause', '')[:200]}...")
        print(f"심각도: {result.get('severity')}")
        print(f"복구 상태: {result.get('recovery_status')}")
        
        if result.get("suggested_actions"):
            print(f"\n제안된 액션: {len(result['suggested_actions'])}개")
            for i, action in enumerate(result["suggested_actions"], 1):
                print(f"  {i}. {action.get('type')}: {action.get('description', '')}")
        
        if result.get("error"):
            print(f"\n에러: {result['error']}")
        
        # 결과를 JSON 파일로 저장
        output_file = "workflow_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n결과가 {output_file}에 저장되었습니다.")
        
    except Exception as e:
        logger.error(f"워크플로우 실행 실패: {str(e)}")
        raise


if __name__ == "__main__":
    main()
