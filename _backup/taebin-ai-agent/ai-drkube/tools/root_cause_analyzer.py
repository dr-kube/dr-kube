"""
근본 원인 분석 모듈
Gemini LLM을 사용하여 에러 카테고리 기반으로 근본 원인을 분석합니다.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel


class RootCauseAnalysis(BaseModel):
    """근본 원인 분석 결과"""
    category: str
    root_cause: str
    explanation: str
    suggested_actions: List[str]
    confidence: float  # 0.0 ~ 1.0
    severity: str = "medium"  # critical, high, medium, low - 장애 등급


class RootCauseAnalyzer:
    """근본 원인 분석 클래스"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        """
        초기화
        
        Args:
            api_key: Google Gemini API 키
            model_name: 사용할 모델 이름 (기본값: gemini-pro)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.3,  # 분석이므로 낮은 temperature 사용
        )
        logger.info(f"RootCauseAnalyzer 초기화 완료 (모델: {model_name})")
    
    def analyze_category(self, category: str, error_logs: List[str], 
                        context: Optional[Dict[str, Any]] = None) -> RootCauseAnalysis:
        """
        특정 에러 카테고리에 대한 근본 원인 분석
        
        Args:
            category: 에러 카테고리 이름
            error_logs: 해당 카테고리의 에러 로그 리스트
            context: 추가 컨텍스트 정보 (선택사항)
            
        Returns:
            RootCauseAnalysis 객체
        """
        logger.debug(f"근본 원인 분석 시작: category={category}, error_logs={len(error_logs)}줄")
        # 분석용 프롬프트 구성
        logs_sample = "\n".join(error_logs[:20])  # 최대 20개 로그만 사용
        if len(error_logs) > 20:
            logs_sample += f"\n... (총 {len(error_logs)}개 로그 중 20개만 표시)"
        logger.debug(f"로그 샘플 구성 완료: {len(logs_sample)} 문자 (원본 {len(error_logs)}줄 중 20개 사용)")
        
        # 컨텍스트 정보 구성
        context_parts = []
        
        if context:
            # 선택한 리소스 타입 정보
            if "selected_resource_types" in context:
                resource_types = context["selected_resource_types"]
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
                        context_parts.append(f"대상 리소스 타입: {', '.join(selected_names)}")
            
            # Pod/서비스 메타데이터 정보
            if "pod_metadata" in context and context["pod_metadata"]:
                pod_info = context["pod_metadata"]
                if isinstance(pod_info, list):
                    pod_info = pod_info[0] if pod_info else {}
                
                pod_details = []
                if pod_info.get("pod_name"):
                    pod_details.append(f"Pod 이름: {pod_info.get('pod_name')}")
                if pod_info.get("namespace"):
                    pod_details.append(f"네임스페이스: {pod_info.get('namespace')}")
                if pod_info.get("service_name"):
                    pod_details.append(f"서비스 이름: {pod_info.get('service_name')}")
                if pod_info.get("node_name"):
                    pod_details.append(f"노드: {pod_info.get('node_name')}")
                
                if pod_details:
                    context_parts.append("영향받는 리소스:\n  " + "\n  ".join(pod_details))
            
            # 선택한 카테고리 정보 (다른 카테고리와의 관계 파악)
            if "selected_categories" in context:
                categories = context["selected_categories"]
                if len(categories) > 1:
                    context_parts.append(f"함께 분석 중인 다른 카테고리: {', '.join([c for c in categories if c != category])}")
            
            # 기타 추가 컨텍스트
            other_context = {k: v for k, v in context.items() 
                           if k not in ["selected_resource_types", "pod_metadata", "selected_categories"]}
            if other_context:
                context_parts.append(f"기타 컨텍스트: {other_context}")
        
        context_str = ""
        if context_parts:
            context_str = "\n\n추가 컨텍스트 정보:\n" + "\n".join(f"- {part}" for part in context_parts) + "\n"
        logger.debug(f"컨텍스트 정보 구성 완료: {len(context_parts)}개 항목")
        
        logger.debug(f"LLM 프롬프트 생성 완료, LLM API 호출 시작")
        prompt = f"""당신은 Kubernetes 전문가입니다.
다음 에러 카테고리와 로그를 분석하여 근본 원인을 파악하고 해결 방안을 제시해주세요.

에러 카테고리: {category}
에러 로그:
{logs_sample}
{context_str}

중요: 위의 추가 컨텍스트 정보(리소스 타입, Pod/서비스 정보 등)를 고려하여 구체적이고 실행 가능한 해결 방안을 제시해주세요.

다음 형식으로 분석 결과를 제공해주세요:

1. 근본 원인: [에러의 근본 원인을 명확하게 설명]
2. 설명: [근본 원인에 대한 상세 설명]
3. 권장 조치사항: [구체적인 해결 방안을 번호로 나열 (특히 위의 리소스 타입에 맞는 조치사항 포함)]
4. 장애 등급: [critical, high, medium, low 중 하나 선택]
   - critical: 즉시 조치 필요, 서비스 중단 또는 데이터 손실 위험
   - high: 빠른 조치 권장, 서비스 성능 저하 또는 일부 기능 불가
   - medium: 조치 필요, 일시적 문제 또는 제한적 영향
   - low: 모니터링 권장, 경미한 문제 또는 자동 복구 가능
5. 신뢰도: [분석의 신뢰도를 0.0~1.0 사이의 숫자로 표현]

분석 결과:"""
        
        try:
            logger.debug(f"LLM API 호출: category={category}, prompt 길이={len(prompt)}")
            response = self.llm.invoke(prompt)
            analysis_text = response.content
            logger.debug(f"LLM API 응답 수신: 응답 길이={len(analysis_text)}")
            
            # 응답 파싱
            logger.debug(f"LLM 응답 파싱 시작: category={category}")
            analysis = self._parse_analysis_response(
                category, error_logs, analysis_text
            )
            logger.debug(f"응답 파싱 완료: root_cause 길이={len(analysis.root_cause)}, confidence={analysis.confidence}, severity={analysis.severity}, actions={len(analysis.suggested_actions)}")
            
            logger.info(f"근본 원인 분석 완료: {category} (신뢰도: {analysis.confidence:.2f})")
            return analysis
        
        except Exception as e:
            logger.error(f"근본 원인 분석 중 오류 발생: {e}")
            # 오류 발생 시 기본 분석 결과 반환
            return RootCauseAnalysis(
                category=category,
                root_cause="분석 중 오류가 발생했습니다",
                explanation=str(e),
                suggested_actions=["로그를 다시 확인하세요", "시스템 상태를 점검하세요"],
                confidence=0.0,
                severity="medium"
            )
    
    def analyze_multiple_categories(self, classified_logs: Dict[str, List[str]],
                                   context: Optional[Dict[str, Any]] = None) -> List[RootCauseAnalysis]:
        """
        여러 에러 카테고리에 대한 근본 원인 분석
        
        Args:
            classified_logs: 카테고리별로 분류된 로그 딕셔너리
            context: 추가 컨텍스트 정보
            
        Returns:
            RootCauseAnalysis 객체 리스트
        """
        logger.debug(f"다중 카테고리 분석 시작: {len(classified_logs)}개 카테고리")
        analyses = []
        
        for idx, (category, logs) in enumerate(classified_logs.items(), 1):
            if not logs:
                logger.debug(f"카테고리 {idx}/{len(classified_logs)} '{category}' 로그 없음, 건너뜀")
                continue
            
            logger.debug(f"카테고리 {idx}/{len(classified_logs)} 분석 시작: {category} ({len(logs)}줄)")
            analysis = self.analyze_category(category, logs, context)
            analyses.append(analysis)
            logger.debug(f"카테고리 {idx}/{len(classified_logs)} 분석 완료: {category}")
        
        # 신뢰도 순으로 정렬 (높은 순)
        logger.debug(f"분석 결과 정렬 시작: {len(analyses)}개")
        analyses.sort(key=lambda x: x.confidence, reverse=True)
        logger.debug(f"분석 결과 정렬 완료: 신뢰도 순위={[(a.category, f'{a.confidence:.2f}') for a in analyses]}")
        
        logger.info(f"총 {len(analyses)}개 카테고리에 대한 근본 원인 분석 완료")
        return analyses
    
    def _parse_analysis_response(self, category: str, error_logs: List[str],
                                 response_text: str) -> RootCauseAnalysis:
        """
        LLM 응답을 파싱하여 RootCauseAnalysis 객체 생성
        
        Args:
            category: 에러 카테고리
            error_logs: 에러 로그 리스트
            response_text: LLM 응답 텍스트
            
        Returns:
            RootCauseAnalysis 객체
        """
        # 기본값
        root_cause = "분석 결과를 파싱할 수 없습니다"
        explanation = response_text
        suggested_actions = []
        confidence = 0.5
        severity = "medium"  # 기본 장애 등급
        
        try:
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 근본 원인 추출
                if '근본 원인' in line or 'root cause' in line.lower():
                    current_section = 'root_cause'
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        root_cause = parts[1].strip()
                    continue
                
                # 설명 추출
                if '설명' in line or 'explanation' in line.lower():
                    current_section = 'explanation'
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        explanation = parts[1].strip()
                    continue
                
                # 권장 조치사항 추출
                if '권장 조치' in line or 'suggested' in line.lower() or 'action' in line.lower():
                    current_section = 'actions'
                    continue
                
                # 장애 등급 추출
                if '장애 등급' in line or 'severity' in line.lower() or '등급' in line:
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        severity_value = parts[1].strip().lower()
                        if severity_value in ['critical', 'high', 'medium', 'low']:
                            severity = severity_value
                    continue
                
                # 신뢰도 추출
                if '신뢰도' in line or 'confidence' in line.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        try:
                            confidence = float(parts[1].strip())
                        except ValueError:
                            pass
                    continue
                
                # 현재 섹션에 따라 데이터 추가
                if current_section == 'root_cause' and not root_cause.startswith('분석'):
                    root_cause = line
                elif current_section == 'explanation':
                    if explanation == response_text:
                        explanation = line
                    else:
                        explanation += " " + line
                elif current_section == 'actions':
                    # 번호나 불릿 포인트 제거
                    action = line.lstrip('0123456789.-* ').strip()
                    if action:
                        suggested_actions.append(action)
                
                # 섹션별로 데이터 누적
                if current_section == 'root_cause' and line and not line.startswith('근본'):
                    root_cause = line
                elif current_section == 'explanation' and line and not line.startswith('설명'):
                    if explanation == response_text:
                        explanation = line
                    else:
                        explanation += " " + line
        
        except Exception as e:
            logger.warning(f"응답 파싱 중 오류: {e}, 원본 응답 사용")
        
        # 조치사항이 없으면 기본값 추가
        if not suggested_actions:
            suggested_actions = [
                "로그를 자세히 검토하세요",
                "시스템 리소스 상태를 확인하세요",
                "관련 서비스 상태를 점검하세요"
            ]
        
        return RootCauseAnalysis(
            category=category,
            root_cause=root_cause,
            explanation=explanation,
            suggested_actions=suggested_actions,
            confidence=confidence,
            severity=severity
        )

