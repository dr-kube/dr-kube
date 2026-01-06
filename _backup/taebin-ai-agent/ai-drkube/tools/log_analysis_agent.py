"""
로그 분석 에이전트 메인 스크립트
전체 워크플로우를 관리하는 메인 에이전트입니다.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv

# 로컬 모듈 import
from .log_collector import LogCollector
from .error_classifier import ErrorClassifier
from .root_cause_analyzer import RootCauseAnalyzer
from .git_action import GitActionGenerator


class LogAnalysisAgent:
    """로그 분석 에이전트 메인 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리 (None이면 환경 변수에서 로드)
        """
        # 환경 변수 로드
        load_dotenv()
        
        # 설정 로드
        self.config = config or self._load_config()
        
        # 컴포넌트 초기화
        self.log_collector = LogCollector(
            kubeconfig_path=self.config.get("kubeconfig_path")
        )
        self.error_classifier = ErrorClassifier()
        
        api_key = self.config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다")
        
        self.analyzer = RootCauseAnalyzer(
            api_key=api_key,
            model_name=self.config.get("model_name", "gemini-2.5-flash")
        )
        
        self.git_action_generator = GitActionGenerator(
            repo_path=self.config.get("repo_path", "."),
            simulate=self.config.get("simulate", True)
        )
        
        logger.info("LogAnalysisAgent 초기화 완료")
    
    def _load_config(self) -> Dict[str, Any]:
        """환경 변수에서 설정 로드"""
        return {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "kubeconfig_path": os.getenv("KUBECONFIG_PATH"),
            "repo_path": os.getenv("REPO_PATH", "."),
            "simulate": os.getenv("SIMULATE", "true").lower() == "true",
            "model_name": os.getenv("MODEL_NAME", "gemini-2.5-flash"),
            "auto_approve": os.getenv("AUTO_APPROVE", "true").lower() == "true",
            "interactive_mode": os.getenv("INTERACTIVE_MODE", "true").lower() == "true",
        }
    
    def run(self, log_source: Optional[Any] = None, source_type: Optional[str] = None, 
           additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        전체 워크플로우 실행
        
        Args:
            log_source: 로그 소스 (파일 경로, Pod 이름, 라벨 셀렉터, 또는 로그 라인 리스트). None이면 상호작용으로 선택
            source_type: 소스 타입 (file, directory, pod, label, stdin, list). None이면 상호작용으로 선택
            additional_context: 추가 컨텍스트 정보
            
        Returns:
            실행 결과 딕셔너리
        """
        result = {
            "status": "success",
            "steps": {},
            "analyses": [],
            "actions": [],
            "summary": {}
        }
        
        try:
            # 0. 로그 소스 선택 (상호작용 모드이고 지정되지 않은 경우)
            if log_source is None or source_type is None:
                logger.info("=== 0단계: 로그 소스 선택 ===")
                selected_source = self._select_log_source_interactive()
                if not selected_source:
                    logger.info("로그 소스 선택이 취소되었습니다.")
                    result["status"] = "cancelled"
                    result["steps"]["log_source_selection"] = {
                        "status": "cancelled",
                        "message": "사용자가 로그 소스 선택을 취소했습니다."
                    }
                    return result
                log_source = selected_source["source"]
                source_type = selected_source["type"]
                logger.info(f"로그 소스 선택 완료: {log_source} (타입: {source_type})")
            
            logger.info(f"로그 분석 에이전트 시작 (소스: {log_source}, 타입: {source_type})")
            logger.debug(f"워크플로우 시작: log_source={log_source}, source_type={source_type}, additional_context={additional_context}")
            
            # 1. 로그 수집
            logger.info("=== 1단계: 로그 수집 ===")
            logger.debug(f"로그 수집 시작: source={log_source}, type={source_type}")
            logs = self._collect_logs(log_source, source_type)
            logger.debug(f"로그 수집 완료: {len(logs) if isinstance(logs, list) else sum(len(v) for v in logs.values())}줄")
            if not logs:
                logger.debug("수집된 로그 없음 - ValueError 발생")
                raise ValueError("수집된 로그가 없습니다")
            
            # Pod/서비스 메타데이터 수집
            pod_metadata = None
            if source_type in ["pod", "label"]:
                # Kubernetes 소스에서 직접 수집
                pod_metadata = self._collect_pod_metadata(log_source, source_type)
                if pod_metadata:
                    logger.info(f"Pod/서비스 메타데이터 수집 완료: {len(pod_metadata) if isinstance(pod_metadata, list) else 1}개")
            elif source_type == "file":
                # 파일에서 로그를 읽은 경우, 로그 내용에서 Pod/서비스 정보 추출 시도
                namespace = self.config.get("kubernetes_namespace", "default")
                pod_metadata = self.log_collector.extract_pod_info_from_logs(logs, namespace)
                if pod_metadata:
                    logger.info("로그 내용에서 Pod/서비스 정보 추출 완료")
                else:
                    logger.debug("로그에서 Pod/서비스 정보를 찾을 수 없습니다")
            
            result["steps"]["log_collection"] = {
                "status": "success",
                "log_count": len(logs) if isinstance(logs, list) else sum(len(v) for v in logs.values()),
                "pod_metadata": pod_metadata
            }
            logger.info(f"로그 수집 완료: {result['steps']['log_collection']['log_count']}줄")
            
            # 로그를 리스트로 변환 (여러 소스에서 수집한 경우)
            if isinstance(logs, dict):
                all_logs = []
                for source_logs in logs.values():
                    all_logs.extend(source_logs)
                logs = all_logs
            
            # 2. 에러 분류
            logger.info("=== 2단계: 에러 분류 ===")
            logger.debug(f"에러 분류 시작: {len(logs)}줄 로그")
            classified_logs = self.error_classifier.classify_logs(logs)
            error_summary = self.error_classifier.get_error_summary(classified_logs)
            logger.debug(f"에러 분류 완료: {len(classified_logs)}개 카테고리, 요약={error_summary}")
            
            result["steps"]["error_classification"] = {
                "status": "success",
                "categories": list(classified_logs.keys()),
                "summary": error_summary
            }
            logger.info(f"에러 분류 완료: {len(classified_logs)}개 카테고리")
            
            # 2.5. 카테고리 선택 (상호작용 모드)
            selected_categories = None
            selected_resource_types = ["all"]  # 기본값
            interactive_mode = self.config.get("interactive_mode", True)
            
            if interactive_mode:
                logger.info("=== 2.5단계: 카테고리 선택 ===")
                selected_categories = self._select_categories_interactive(classified_logs, error_summary)
                
                if not selected_categories:
                    logger.info("선택된 카테고리가 없습니다. 프로세스를 중단합니다.")
                    result["status"] = "cancelled"
                    result["steps"]["category_selection"] = {
                        "status": "cancelled",
                        "message": "사용자가 카테고리 선택을 취소했습니다."
                    }
                    return result
                
                # 선택한 카테고리만 필터링
                filtered_classified_logs = {
                    cat: logs for cat, logs in classified_logs.items() 
                    if cat in selected_categories
                }
                
                result["steps"]["category_selection"] = {
                    "status": "success",
                    "selected_categories": selected_categories,
                    "total_categories": len(classified_logs),
                    "selected_count": len(selected_categories)
                }
                logger.info(f"카테고리 선택 완료: {len(selected_categories)}개 선택 (전체 {len(classified_logs)}개 중)")
                
                # 필터링된 로그로 교체
                classified_logs = filtered_classified_logs
                # 필터링된 로그에 대한 요약 정보 재생성
                error_summary = self.error_classifier.get_error_summary(classified_logs)
                
                # 2.6. 리소스 타입 선택 (상호작용 모드)
                logger.info("=== 2.6단계: 리소스 타입 선택 ===")
                selected_resource_types = self._select_resource_types_interactive(selected_categories, pod_metadata)
                
                result["steps"]["resource_type_selection"] = {
                    "status": "success",
                    "selected_resource_types": selected_resource_types
                }
                logger.info(f"리소스 타입 선택 완료: {', '.join(selected_resource_types)}")
            else:
                logger.info("비상호작용 모드: 모든 카테고리를 분석합니다.")
                result["steps"]["category_selection"] = {
                    "status": "skipped",
                    "message": "비상호작용 모드 - 모든 카테고리 분석"
                }
                result["steps"]["resource_type_selection"] = {
                    "status": "skipped",
                    "message": "비상호작용 모드 - 모든 리소스 타입"
                }
            
            # 3. 근본 원인 분석
            logger.info("=== 3단계: 근본 원인 분석 ===")
            
            # 분석 컨텍스트 구성 (선택한 카테고리, 리소스 타입, Pod 메타데이터 포함)
            analysis_context = additional_context or {}
            # 선택한 카테고리 정보 (비상호작용 모드에서는 모든 카테고리)
            if selected_categories is None:
                selected_categories = list(classified_logs.keys())
            
            analysis_context.update({
                "selected_categories": selected_categories,
                "selected_resource_types": selected_resource_types,
                "pod_metadata": pod_metadata
            })
            logger.debug(f"근본 원인 분석 컨텍스트: selected_categories={selected_categories}, selected_resource_types={selected_resource_types}, pod_metadata={pod_metadata is not None}")
            
            logger.debug(f"근본 원인 분석 시작: {len(classified_logs)}개 카테고리")
            analyses = self.analyzer.analyze_multiple_categories(
                classified_logs,
                context=analysis_context
            )
            logger.debug(f"근본 원인 분석 완료: {len(analyses)}개 분석 결과")
            
            result["analyses"] = [
                {
                    "category": a.category,
                    "root_cause": a.root_cause,
                    "explanation": a.explanation,
                    "suggested_actions": a.suggested_actions,
                    "confidence": a.confidence,
                    "severity": getattr(a, 'severity', 'medium')
                }
                for a in analyses
            ]
            result["steps"]["root_cause_analysis"] = {
                "status": "success",
                "analysis_count": len(analyses)
            }
            logger.info(f"근본 원인 분석 완료: {len(analyses)}개 카테고리")
            
            # 4. 사용자 피드백 (Phase 1: 자동 승인)
            logger.info("=== 4단계: 사용자 피드백 ===")
            if self.config.get("auto_approve", True):
                logger.info("자동 승인 모드: 분석 결과를 자동으로 승인합니다")
                approved = True
            else:
                approved = self._show_user_feedback(analyses, error_summary)
            
            result["steps"]["user_feedback"] = {
                "status": "success" if approved else "rejected",
                "approved": approved
            }
            
            if not approved:
                logger.info("사용자가 분석 결과를 거부했습니다. 프로세스를 중단합니다.")
                result["status"] = "rejected"
                return result
            
            # 5. 액션 생성
            logger.info("=== 5단계: Git 액션 생성 ===")
            logger.debug(f"Git 액션 생성 시작: analyses={len(analyses)}개, resource_types={selected_resource_types}")
            # 리소스 타입 선택 정보 전달
            actions = self.git_action_generator.generate_actions_from_analysis(
                analyses, error_summary, pod_metadata=pod_metadata, resource_types=selected_resource_types
            )
            logger.debug(f"Git 액션 생성 완료: {len(actions)}개 액션")
            
            result["actions"] = [
                {
                    "type": a.action_type,
                    "file_path": a.file_path,
                    "description": a.description
                }
                for a in actions
            ]
            result["steps"]["action_generation"] = {
                "status": "success",
                "action_count": len(actions)
            }
            logger.info(f"Git 액션 생성 완료: {len(actions)}개")
            
            # 6. Git 커밋 (Phase 1: 시뮬레이션)
            logger.info("=== 6단계: Git 액션 적용 및 커밋 ===")
            logger.debug(f"Git 액션 적용 시작: {len(actions)}개 액션")
            actions_applied = self.git_action_generator.apply_actions(actions)
            logger.debug(f"Git 액션 적용 결과: {actions_applied}")
            
            if actions_applied:
                commit_message = self._generate_commit_message(analyses, error_summary)
                logger.debug(f"커밋 메시지 생성: {commit_message}")
                commit_success = self.git_action_generator.commit_changes(commit_message)
                logger.debug(f"Git 커밋 결과: {commit_success}")
                
                result["steps"]["git_commit"] = {
                    "status": "success" if commit_success else "failed",
                    "commit_message": commit_message,
                    "simulated": self.config.get("simulate", True)
                }
                logger.info(f"Git 커밋 완료 (시뮬레이션: {self.config.get('simulate', True)})")
            else:
                result["steps"]["git_commit"] = {
                    "status": "failed",
                    "reason": "액션 적용 실패"
                }
            
            # 7. 복구 검증 (Phase 1: 시뮬레이션)
            logger.info("=== 7단계: 복구 검증 ===")
            verification_result = self._verify_recovery(analyses, actions)
            
            result["steps"]["recovery_verification"] = {
                "status": "simulated",
                "result": verification_result
            }
            logger.info("복구 검증 완료 (시뮬레이션)")
            
            # 8. 최종 피드백
            logger.info("=== 8단계: 최종 피드백 ===")
            final_feedback = self._generate_final_feedback(result)
            result["summary"] = final_feedback
            
            self._show_final_feedback(final_feedback)
            
            logger.info("=== 로그 분석 에이전트 완료 ===")
            return result
        
        except Exception as e:
            logger.error(f"에이전트 실행 중 오류 발생: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            return result
    
    def _collect_logs(self, log_source: Any, source_type: str) -> Any:
        """
        로그 수집 헬퍼 메서드
        
        Args:
            log_source: 로그 소스 (파일 경로, Pod 이름, 라벨 셀렉터, 또는 로그 라인 리스트)
            source_type: 소스 타입 (file, directory, pod, label, stdin, list)
        """
        # 리스트인 경우 직접 처리
        if isinstance(log_source, list):
            logger.debug(f"리스트 타입 로그 소스 감지: {len(log_source)}줄")
            return self.log_collector.collect_from_list(log_source)
        
        if source_type == "file":
            return self.log_collector.collect_from_file(log_source)
        elif source_type == "directory":
            return self.log_collector.collect_from_directory(log_source)
        elif source_type == "pod":
            namespace = self.config.get("kubernetes_namespace", "default")
            return self.log_collector.collect_from_pod(log_source, namespace)
        elif source_type == "label":
            namespace = self.config.get("kubernetes_namespace", "default")
            return self.log_collector.collect_from_pods_by_label(log_source, namespace)
        elif source_type == "stdin":
            return self.log_collector.collect_from_stdin()
        else:
            raise ValueError(f"지원하지 않는 소스 타입: {source_type}")
    
    def _select_log_source_interactive(self) -> Optional[Dict[str, str]]:
        """
        상호작용형 로그 소스 선택 UI
        
        Returns:
            {"source": log_source, "type": source_type} 딕셔너리 또는 None
        """
        print("\n" + "="*80)
        print("로그 소스 선택")
        print("="*80)
        print("\n로그를 수집할 소스를 선택하세요:\n")
        
        source_types = [
            ("로컬 파일", "file", "로컬 파일 시스템의 로그 파일"),
            ("디렉토리", "directory", "디렉토리 내 모든 로그 파일"),
            ("Kubernetes Pod", "pod", "특정 Kubernetes Pod의 로그"),
            ("라벨 셀렉터", "label", "라벨로 선택된 여러 Pod의 로그"),
            ("표준 입력", "stdin", "표준 입력에서 로그 읽기"),
        ]
        
        for idx, (name, value, description) in enumerate(source_types, 1):
            print(f"  [{idx}] {name} ({value})")
            print(f"      - {description}")
        
        print("\n" + "-"*80)
        print("입력 형식:")
        print("  - 번호 선택: 1, 2, 3 등")
        print("  - 타입 이름: file, pod, label 등")
        print("  - 취소: quit 또는 exit")
        print("-"*80)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user_input = input("\n로그 소스 타입을 선택하세요: ").strip()
                
                if not user_input:
                    print("⚠️  입력이 비어있습니다. 다시 입력해주세요.")
                    continue
                
                # 취소 처리
                if user_input.lower() in ['quit', 'exit', 'q']:
                    return None
                
                # 타입 선택 파싱
                selected_type = None
                try:
                    idx = int(user_input)
                    if 1 <= idx <= len(source_types):
                        selected_type = source_types[idx - 1][1]
                except ValueError:
                    # 타입 이름으로 입력한 경우
                    user_input_lower = user_input.lower()
                    for name, value, _ in source_types:
                        if user_input_lower == name.lower() or user_input_lower == value.lower():
                            selected_type = value
                            break
                
                if not selected_type:
                    print(f"⚠️  잘못된 입력입니다. 다시 입력해주세요. (남은 시도: {max_retries - attempt - 1})")
                    continue
                
                # 선택한 타입에 따라 소스 입력 요청
                source = self._get_source_input(selected_type)
                if source is None:
                    return None
                
                return {"source": source, "type": selected_type}
            
            except KeyboardInterrupt:
                print("\n\n사용자가 중단했습니다.")
                return None
            except Exception as e:
                logger.error(f"입력 처리 중 오류: {e}")
                print(f"⚠️  오류가 발생했습니다: {e}")
        
        return None
    
    def _get_source_input(self, source_type: str) -> Optional[str]:
        """
        선택한 소스 타입에 따라 소스 입력 요청
        
        Args:
            source_type: 선택한 소스 타입
            
        Returns:
            로그 소스 문자열 또는 None
        """
        if source_type == "file":
            print("\n로컬 파일 경로를 입력하세요:")
            print("  예시: tools/sample_error.log, /var/log/app/error.log")
            source = input("파일 경로: ").strip()
            if not source:
                # 기본값 사용
                source = "tools/sample_error.log"
                print(f"기본값 사용: {source}")
            return source
        
        elif source_type == "directory":
            print("\n디렉토리 경로를 입력하세요:")
            print("  예시: ./logs, /var/log/app")
            source = input("디렉토리 경로: ").strip()
            return source if source else None
        
        elif source_type == "pod":
            print("\nKubernetes Pod 이름을 입력하세요:")
            print("  예시: argocd-server-766b6bbb64-k7wch")
            # Pod 목록 표시 시도
            try:
                import subprocess
                result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "default", "-o", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    print("\n사용 가능한 Pod 목록:")
                    pods = result.stdout.strip().split('\n')[:10]  # 최대 10개만 표시
                    for pod in pods:
                        print(f"  - {pod.replace('pod/', '')}")
            except Exception:
                pass  # kubectl이 없거나 실패해도 계속 진행
            source = input("Pod 이름: ").strip()
            return source if source else None
        
        elif source_type == "label":
            print("\n라벨 셀렉터를 입력하세요:")
            print("  예시: app.kubernetes.io/name=argocd, app=myapp")
            source = input("라벨 셀렉터: ").strip()
            return source if source else None
        
        elif source_type == "stdin":
            print("\n표준 입력에서 로그를 읽습니다.")
            print("로그를 입력한 후 Ctrl+D (Mac/Linux) 또는 Ctrl+Z (Windows)로 종료하세요.")
            return ""  # stdin은 빈 문자열로 표시
        
        return None
    
    def _collect_pod_metadata(self, log_source: str, source_type: str) -> Optional[Any]:
        """Pod/서비스 메타데이터 수집 헬퍼 메서드"""
        if source_type == "pod":
            namespace = self.config.get("kubernetes_namespace", "default")
            return self.log_collector.get_pod_metadata(log_source, namespace)
        elif source_type == "label":
            namespace = self.config.get("kubernetes_namespace", "default")
            return self.log_collector.get_pods_metadata_by_label(log_source, namespace)
        return None
    
    def _select_categories_interactive(self, classified_logs: Dict[str, List[str]], 
                                      error_summary: Dict[str, Any]) -> List[str]:
        """
        상호작용형 카테고리 선택 UI
        
        Args:
            classified_logs: 카테고리별로 분류된 로그 딕셔너리
            error_summary: 에러 요약 정보
            
        Returns:
            선택된 카테고리 이름 리스트
        """
        if not classified_logs:
            logger.warning("분류된 카테고리가 없습니다")
            return []
        
        # 카테고리 목록 준비
        categories = list(classified_logs.keys())
        category_info = error_summary.get("categories", {})
        
        # 카테고리별 심각도 정보 가져오기
        severity_map = {}
        for cat_name, info in category_info.items():
            severity_map[cat_name] = info.get("severity", "low")
        
        # 심각도 순으로 정렬 (critical > high > medium > low)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        categories.sort(key=lambda x: severity_order.get(severity_map.get(x, "low"), 3))
        
        # UI 표시
        print("\n" + "="*80)
        print("에러 카테고리 선택")
        print("="*80)
        print(f"\n총 {len(categories)}개 카테고리가 발견되었습니다.\n")
        print("발견된 카테고리:")
        
        for idx, category in enumerate(categories, 1):
            error_count = len(classified_logs[category])
            severity = severity_map.get(category, "low")
            severity_kr = {"critical": "치명적", "high": "높음", "medium": "보통", "low": "낮음"}.get(severity, "낮음")
            
            # 심각도에 따른 표시
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(severity, "⚪")
            
            print(f"  [{idx}] {severity_icon} {category}")
            print(f"      - 에러 수: {error_count}개")
            print(f"      - 심각도: {severity_kr} ({severity})")
        
        print("\n" + "-"*80)
        print("입력 형식:")
        print("  - 단일 선택: 1 또는 네트워크 오류")
        print("  - 다중 선택: 1,2,4 또는 네트워크 오류,리소스 부족")
        print("  - 전체 선택: all 또는 *")
        print("  - 취소: quit 또는 exit")
        print("-"*80)
        
        # 사용자 입력 받기 (최대 3번 재시도)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user_input = input("\n분석할 카테고리를 선택하세요: ").strip()
                
                if not user_input:
                    print("⚠️  입력이 비어있습니다. 다시 입력해주세요.")
                    continue
                
                # 취소 처리
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("사용자가 선택을 취소했습니다.")
                    return []
                
                # 전체 선택 처리
                if user_input.lower() in ['all', '*']:
                    logger.info(f"전체 {len(categories)}개 카테고리를 선택했습니다.")
                    return categories
                
                # 선택 파싱
                selected = self._parse_category_selection(user_input, categories)
                
                if selected:
                    logger.info(f"{len(selected)}개 카테고리를 선택했습니다: {', '.join(selected)}")
                    return selected
                else:
                    print(f"⚠️  잘못된 입력입니다. 다시 입력해주세요. (남은 시도: {max_retries - attempt - 1})")
            
            except KeyboardInterrupt:
                print("\n\n사용자가 중단했습니다.")
                return []
            except Exception as e:
                logger.error(f"입력 처리 중 오류: {e}")
                print(f"⚠️  오류가 발생했습니다: {e}")
        
        # 최대 재시도 횟수 초과
        print(f"\n⚠️  최대 재시도 횟수({max_retries})를 초과했습니다. 프로세스를 중단합니다.")
        return []
    
    def _parse_category_selection(self, user_input: str, 
                                  available_categories: List[str]) -> List[str]:
        """
        사용자 입력을 파싱하여 선택된 카테고리 리스트 반환
        
        Args:
            user_input: 사용자 입력 문자열
            available_categories: 사용 가능한 카테고리 리스트
            
        Returns:
            선택된 카테고리 이름 리스트
        """
        selected = []
        
        # 쉼표로 분리
        parts = [p.strip() for p in user_input.split(',')]
        
        for part in parts:
            if not part:
                continue
            
            # 숫자로 입력한 경우
            try:
                idx = int(part)
                if 1 <= idx <= len(available_categories):
                    category = available_categories[idx - 1]
                    if category not in selected:
                        selected.append(category)
                else:
                    logger.warning(f"범위를 벗어난 번호: {idx}")
                    return []
            except ValueError:
                # 카테고리 이름으로 입력한 경우
                # 부분 일치 검색
                matched = [cat for cat in available_categories if part in cat or cat in part]
                if len(matched) == 1:
                    if matched[0] not in selected:
                        selected.append(matched[0])
                elif len(matched) > 1:
                    logger.warning(f"'{part}'와 일치하는 카테고리가 여러 개입니다: {matched}")
                    return []
                else:
                    logger.warning(f"'{part}'와 일치하는 카테고리를 찾을 수 없습니다.")
                    return []
        
        return selected
    
    def _select_resource_types_interactive(self, selected_categories: List[str],
                                          pod_metadata: Optional[Any] = None) -> List[str]:
        """
        상호작용형 리소스 타입 선택 UI
        
        Args:
            selected_categories: 선택된 카테고리 리스트
            pod_metadata: Pod 메타데이터 (있는 경우)
            
        Returns:
            선택된 리소스 타입 리스트
        """
        # Kubernetes 리소스 타입 목록
        resource_types = [
            ("Pod", "pod", "Pod 리소스 설정 및 패치"),
            ("Service", "service", "Service 리소스 설정 및 패치"),
            ("Deployment", "deployment", "Deployment 리소스 설정 및 패치"),
            ("ConfigMap", "configmap", "ConfigMap 리소스 설정 및 패치"),
            ("Secret", "secret", "Secret 리소스 설정 및 패치"),
            ("PersistentVolume", "pv", "PersistentVolume 리소스 설정"),
            ("PersistentVolumeClaim", "pvc", "PersistentVolumeClaim 리소스 설정"),
            ("NetworkPolicy", "networkpolicy", "NetworkPolicy 리소스 설정"),
            ("ResourceQuota", "resourcequota", "ResourceQuota 리소스 설정"),
            ("LimitRange", "limitrange", "LimitRange 리소스 설정"),
        ]
        
        # UI 표시
        print("\n" + "="*80)
        print("리소스 타입 선택")
        print("="*80)
        print(f"\n선택된 카테고리: {', '.join(selected_categories)}")
        print(f"\n분석 리포트에 포함할 Kubernetes 리소스 타입을 선택하세요.\n")
        print("사용 가능한 리소스 타입:")
        
        for idx, (name, value, description) in enumerate(resource_types, 1):
            print(f"  [{idx}] {name} ({value})")
            print(f"      - {description}")
        
        print("\n" + "-"*80)
        print("입력 형식:")
        print("  - 단일 선택: 1 또는 Pod")
        print("  - 다중 선택: 1,2,3 또는 Pod,Service,Deployment")
        print("  - 전체 선택: all 또는 *")
        print("  - 취소: quit 또는 exit")
        print("-"*80)
        
        # 사용자 입력 받기 (최대 3번 재시도)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user_input = input("\n리소스 타입을 선택하세요: ").strip()
                
                if not user_input:
                    print("⚠️  입력이 비어있습니다. 다시 입력해주세요.")
                    continue
                
                # 취소 처리
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("사용자가 리소스 타입 선택을 취소했습니다.")
                    return ["all"]  # 기본값으로 전체 선택
                
                # 전체 선택 처리
                if user_input.lower() in ['all', '*']:
                    logger.info("전체 리소스 타입을 선택했습니다.")
                    return [rt[1] for rt in resource_types]
                
                # 선택 파싱
                selected = self._parse_resource_type_selection(user_input, resource_types)
                
                if selected:
                    logger.info(f"{len(selected)}개 리소스 타입을 선택했습니다: {', '.join(selected)}")
                    return selected
                else:
                    print(f"⚠️  잘못된 입력입니다. 다시 입력해주세요. (남은 시도: {max_retries - attempt - 1})")
            
            except KeyboardInterrupt:
                print("\n\n사용자가 중단했습니다.")
                return ["all"]  # 기본값
            except Exception as e:
                logger.error(f"입력 처리 중 오류: {e}")
                print(f"⚠️  오류가 발생했습니다: {e}")
        
        # 최대 재시도 횟수 초과
        print(f"\n⚠️  최대 재시도 횟수({max_retries})를 초과했습니다. 전체 리소스 타입을 사용합니다.")
        return ["all"]
    
    def _parse_resource_type_selection(self, user_input: str,
                                      available_resource_types: List[tuple]) -> List[str]:
        """
        사용자 입력을 파싱하여 선택된 리소스 타입 리스트 반환
        
        Args:
            user_input: 사용자 입력 문자열
            available_resource_types: 사용 가능한 리소스 타입 리스트 (name, value, description)
            
        Returns:
            선택된 리소스 타입 값 리스트
        """
        selected = []
        
        # 쉼표로 분리
        parts = [p.strip() for p in user_input.split(',')]
        
        for part in parts:
            if not part:
                continue
            
            # 숫자로 입력한 경우
            try:
                idx = int(part)
                if 1 <= idx <= len(available_resource_types):
                    resource_value = available_resource_types[idx - 1][1]
                    if resource_value not in selected:
                        selected.append(resource_value)
                else:
                    logger.warning(f"범위를 벗어난 번호: {idx}")
                    return []
            except ValueError:
                # 리소스 타입 이름이나 값으로 입력한 경우
                part_lower = part.lower()
                matched = None
                
                for name, value, _ in available_resource_types:
                    if part_lower == name.lower() or part_lower == value.lower():
                        matched = value
                        break
                
                if matched:
                    if matched not in selected:
                        selected.append(matched)
                else:
                    logger.warning(f"'{part}'와 일치하는 리소스 타입을 찾을 수 없습니다.")
                    return []
        
        return selected
    
    def _show_user_feedback(self, analyses: List[Any], 
                           error_summary: Dict[str, Any]) -> bool:
        """사용자 피드백 표시 및 승인 여부 확인"""
        print("\n" + "="*80)
        print("분석 결과 요약")
        print("="*80)
        print(f"\n총 에러 수: {error_summary.get('total_errors', 0)}")
        print(f"카테고리 수: {len(analyses)}")
        print("\n심각도 분포:")
        for severity, count in error_summary.get('severity_counts', {}).items():
            print(f"  {severity}: {count}")
        
        print("\n" + "-"*80)
        print("근본 원인 분석 결과")
        print("-"*80)
        
        for i, analysis in enumerate(analyses, 1):
            severity = getattr(analysis, 'severity', 'medium')
            severity_icons = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            severity_icon = severity_icons.get(severity, "⚪")
            
            print(f"\n[{i}] {severity_icon} {analysis.category} (등급: {severity.upper()})")
            print(f"  근본 원인: {analysis.root_cause}")
            print(f"  신뢰도: {analysis.confidence:.2%}")
            print(f"  권장 조치:")
            for action in analysis.suggested_actions[:3]:  # 최대 3개만 표시
                print(f"    - {action}")
        
        print("\n" + "="*80)
        
        # 자동 승인 모드가 아니면 사용자 입력 요청
        if not self.config.get("auto_approve", True):
            response = input("\n이 분석 결과를 승인하시겠습니까? (y/n): ").strip().lower()
            return response in ['y', 'yes', '예']
        
        return True
    
    def _generate_commit_message(self, analyses: List[Any], 
                                 error_summary: Dict[str, Any]) -> str:
        """커밋 메시지 생성"""
        categories = [a.category for a in analyses[:3]]  # 최대 3개 카테고리만
        category_str = ", ".join(categories)
        
        return f"fix: 에러 분석 및 복구 조치 ({category_str})"
    
    def _verify_recovery(self, analyses: List[Any], actions: List[Any]) -> Dict[str, Any]:
        """복구 검증 (Phase 1: 시뮬레이션)"""
        # 시뮬레이션 모드에서는 실제 검증을 수행하지 않음
        return {
            "status": "simulated",
            "message": "복구 검증은 시뮬레이션 모드입니다. 실제 환경에서는 로그를 다시 확인하여 검증해야 합니다.",
            "suggested_checks": [
                "로그에서 동일한 에러가 더 이상 발생하지 않는지 확인",
                "시스템 리소스 상태 점검",
                "서비스 헬스 체크 수행",
                "관련 메트릭 모니터링"
            ]
        }
    
    def _generate_final_feedback(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """최종 피드백 생성"""
        return {
            "total_errors": result.get("steps", {}).get("log_collection", {}).get("log_count", 0),
            "categories_analyzed": len(result.get("analyses", [])),
            "actions_generated": len(result.get("actions", [])),
            "status": result.get("status"),
            "simulated": self.config.get("simulate", True)
        }
    
    def _show_final_feedback(self, feedback: Dict[str, Any]):
        """최종 피드백 표시"""
        print("\n" + "="*80)
        print("최종 결과")
        print("="*80)
        print(f"총 에러 수: {feedback.get('total_errors', 0)}")
        print(f"분석된 카테고리: {feedback.get('categories_analyzed', 0)}")
        print(f"생성된 액션: {feedback.get('actions_generated', 0)}")
        print(f"상태: {feedback.get('status', 'unknown')}")
        print(f"시뮬레이션 모드: {feedback.get('simulated', True)}")
        print("="*80)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="로그 분석 에이전트")
    parser.add_argument(
        "log_source",
        nargs="?",
        default=None,
        help="로그 소스 (파일 경로, Pod 이름, 라벨 셀렉터 등). 생략 시 상호작용으로 선택"
    )
    parser.add_argument(
        "--type",
        choices=["file", "directory", "pod", "label", "stdin"],
        default=None,
        help="로그 소스 타입. 생략 시 상호작용으로 선택"
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Git 저장소 경로 (기본값: 현재 디렉토리)"
    )
    parser.add_argument(
        "--no-simulate",
        action="store_true",
        help="시뮬레이션 모드 비활성화 (실제 파일 변경 및 커밋 수행)"
    )
    parser.add_argument(
        "--no-auto-approve",
        action="store_true",
        help="자동 승인 비활성화 (사용자 승인 요청)"
    )
    parser.add_argument(
        "--kubeconfig",
        help="Kubernetes config 파일 경로"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="상호작용 모드 활성화 (카테고리 선택 UI 표시)"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="상호작용 모드 비활성화 (모든 카테고리 자동 분석)"
    )
    
    args = parser.parse_args()
    
    # interactive_mode 결정 (CLI 옵션이 환경 변수보다 우선)
    if args.interactive:
        interactive_mode = True
    elif args.no_interactive:
        interactive_mode = False
    else:
        # 환경 변수 또는 기본값 사용
        interactive_mode = os.getenv("INTERACTIVE_MODE", "true").lower() == "true"
    
    # 설정 구성
    config = {
        "repo_path": args.repo_path,
        "simulate": not args.no_simulate,
        "auto_approve": not args.no_auto_approve,
        "kubeconfig_path": args.kubeconfig,
        "interactive_mode": interactive_mode,
    }
    
    # 에이전트 생성 및 실행
    try:
        agent = LogAnalysisAgent(config=config)
        result = agent.run(args.log_source, args.type)
        
        # 결과에 따라 종료 코드 설정
        if result.get("status") == "success":
            sys.exit(0)
        else:
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"에이전트 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()