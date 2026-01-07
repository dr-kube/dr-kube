"""액션 생성 노드"""
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langraph.models.state import IncidentState
from langraph.utils.logger import get_logger
from langraph.services.app_of_apps_analyzer import AppOfAppsAnalyzer
from langraph.services.yaml_modifier import YamlModifier

logger = get_logger(__name__)


def generate_action_node(state: IncidentState) -> Dict[str, Any]:
    """
    승인된 액션에 따라 Git 변경사항을 생성하는 노드
    
    App of Apps 구조를 분석하여 실제 values.yaml 파일을 수정
    """
    logger.info("액션 생성 시작")
    
    approved_action = state.get("user_approved_action", "")
    affected_apps = state.get("affected_apps", [])
    error_category = state.get("error_category", "")
    dry_run = state.get("dry_run", False)
    repo_root = state.get("repo_root", ".")
    
    # App of Apps 구조 분석
    analyzer = AppOfAppsAnalyzer(repo_root=repo_root)
    analyzer.analyze()
    
    modified_files = []
    git_changes = {}
    modifiers_map = {}  # app_name -> modifier 매핑 (나중에 diff 생성용)
    
    # 각 영향받는 앱에 대해 파일 수정
    for app_name in affected_apps:
        values_path = analyzer.get_values_path(app_name)
        
        if not values_path:
            logger.warning(f"{app_name}의 values.yaml을 찾을 수 없습니다")
            continue
        
        try:
            modifier = YamlModifier(values_path, repo_root=repo_root)
            modifier.load()
            
            # 에러 카테고리에 따라 다른 액션 수행
            if error_category == "oom":
                # 메모리 제한 증가
                modifier.increase_memory_limit(memory_increase="512Mi")
                content = modifier.get_content()
                git_changes[values_path] = content
                modifier.save(dry_run=dry_run)
                modified_files.append(values_path)
                modifiers_map[app_name] = modifier  # diff 생성을 위해 저장
                logger.info(f"{app_name}의 메모리 제한 증가 완료")
                
            elif error_category == "crashloop":
                # 기본적으로는 로그만 남기고, 향후 더 구체적인 액션 추가 가능
                logger.info(f"{app_name}의 crashloop 에러 - 수동 확인 필요")
                
            # 다른 에러 카테고리에 대한 처리 추가 가능
            
        except Exception as e:
            logger.error(f"{app_name} 파일 수정 실패: {e}")
    
    commit_message = f"fix: {error_category} 에러 복구 - {approved_action}"
    
    # 예시 파일들을 incident별 폴더에 저장 (diff 형식)
    try:
        from shutil import copy2
        from datetime import datetime
        
        repo_path = Path(repo_root)
        examples_base_dir = repo_path / "dr-kube" / "langraph" / "examples"
        
        # langraph가 repo_root 바로 아래에 있는 경우도 시도
        if not examples_base_dir.exists():
            examples_base_dir = repo_path / "langraph" / "examples"
        
        examples_base_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        incident_id = state.get("incident_id", "unknown")
        
        # incident별 폴더 생성
        incident_dir = examples_base_dir / incident_id
        incident_dir.mkdir(parents=True, exist_ok=True)
        
        example_files = []
        
        # 1. 수정된 파일들의 diff 저장
        for app_name, values_path in zip(affected_apps, modified_files[:]):
            try:
                # 이미 수정한 modifier에서 diff 가져오기
                modifier = modifiers_map.get(app_name)
                if not modifier:
                    logger.warning(f"{app_name}의 modifier를 찾을 수 없습니다. 새로 로드합니다.")
                    modifier = YamlModifier(values_path, repo_root=repo_root)
                    modifier.load()
                
                # diff 생성
                diff_content = modifier.get_diff()
                
                # diff 파일 저장
                diff_filename = f"{app_name}_values.diff"
                diff_path = incident_dir / diff_filename
                
                with open(diff_path, "w", encoding="utf-8") as f:
                    f.write(f"# Diff for {values_path}\n")
                    f.write(f"# Incident: {incident_id}\n")
                    f.write(f"# Error Category: {error_category}\n")
                    f.write(f"# Timestamp: {timestamp}\n\n")
                    f.write(diff_content)
                
                try:
                    relative_path = diff_path.relative_to(repo_path)
                    example_files.append(str(relative_path))
                    logger.info(f"Diff 파일 생성: {diff_path}")
                except ValueError:
                    example_files.append(str(diff_path))
                    logger.info(f"Diff 파일 생성 (절대 경로): {diff_path}")
                    
            except Exception as e:
                logger.warning(f"Diff 생성 실패 ({values_path}): {e}")
        
        # 2. 예시 로그 파일도 복사
        log_file_path = state.get("log_file_path")
        if log_file_path:
            source_file = Path(log_file_path)
            if not source_file.is_absolute():
                source_file = Path.cwd() / log_file_path
            
            if source_file.exists():
                log_filename = f"original_log_{error_category}.txt"
                log_path = incident_dir / log_filename
                
                copy2(source_file, log_path)
                
                try:
                    relative_path = log_path.relative_to(repo_path)
                    example_files.append(str(relative_path))
                    logger.info(f"예시 로그 파일 복사: {log_path}")
                except ValueError:
                    example_files.append(str(log_path))
                    logger.info(f"예시 로그 파일 복사 (절대 경로): {log_path}")
        
        # 3. 인시던트 요약 정보 저장
        summary_path = incident_dir / "summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Incident Summary: {incident_id}\n\n")
            f.write(f"## 기본 정보\n")
            f.write(f"- **Incident ID**: {incident_id}\n")
            f.write(f"- **Error Category**: {error_category}\n")
            f.write(f"- **Error Severity**: {state.get('error_severity', 'unknown')}\n")
            f.write(f"- **Timestamp**: {timestamp}\n\n")
            f.write(f"## 영향받는 애플리케이션\n")
            for app in affected_apps:
                f.write(f"- {app}\n")
            f.write(f"\n## 근본 원인\n")
            f.write(f"{state.get('root_cause', 'N/A')}\n\n")
            f.write(f"## 승인된 액션\n")
            f.write(f"{approved_action}\n\n")
            f.write(f"## 커밋 메시지\n")
            f.write(f"```\n{commit_message}\n```\n")
        
        try:
            relative_path = summary_path.relative_to(repo_path)
            example_files.append(str(relative_path))
        except ValueError:
            example_files.append(str(summary_path))
        
        # 예시 파일들을 modified_files에 추가 (커밋에 포함)
        modified_files.extend(example_files)
        logger.info(f"인시던트 폴더 생성: {incident_dir}")
        
    except Exception as e:
        logger.warning(f"예시 파일 생성 실패 (무시): {e}")
    
    if dry_run:
        logger.info(f"[DRY-RUN] 파일 수정 완료 ({len(modified_files)}개 파일, 커밋은 안 함)")
    else:
        logger.info(f"파일 수정 완료: {len(modified_files)}개 파일")
    
    return {
        "git_changes": git_changes,
        "commit_message": commit_message,
        "modified_files": modified_files,
        "workflow_status": "action_generated",
    }

