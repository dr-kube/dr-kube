"""
Gemini LLM 호출 도구
새로운 google.genai SDK 사용
"""
import os
import json
from typing import Optional


_client = None
_mock_mode = False


def is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return not os.getenv("GEMINI_API_KEY")


def get_client():
    """Gemini Client 싱글톤"""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        from google import genai
        _client = genai.Client(api_key=api_key)
    return _client


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON 파싱"""
    text = text.strip()
    # 코드 블록 제거
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def _parse_memory(mem_str: str) -> int:
    """메모리 문자열을 Mi 단위 정수로 변환"""
    if not mem_str:
        return 128
    mem_str = mem_str.strip()
    if mem_str.endswith("Gi"):
        return int(float(mem_str[:-2]) * 1024)
    elif mem_str.endswith("Mi"):
        return int(float(mem_str[:-2]))
    elif mem_str.endswith("Ki"):
        return int(float(mem_str[:-2]) / 1024)
    else:
        # 숫자만 있으면 바이트로 가정
        try:
            return int(int(mem_str) / (1024 * 1024))
        except:
            return 128


def _format_memory(mi_value: int) -> str:
    """Mi 값을 적절한 단위로 포맷"""
    if mi_value >= 1024:
        return f"{mi_value // 1024}Gi"
    return f"{mi_value}Mi"


def analyze_oom_issue(
    pod_details: dict,
    events: list[dict],
    logs: str,
    restart_count: int
) -> dict:
    """OOMKilled 이슈 분석"""
    client = get_client()
    
    # LLM 없으면 규칙 기반 분석
    if client is None:
        current_limit = pod_details.get('memory_limit', '128Mi')
        # 간단한 규칙: 현재 limit의 2배 권장
        limit_value = _parse_memory(current_limit)
        new_limit = _format_memory(limit_value * 2)
        new_request = _format_memory(limit_value)
        
        return {
            "root_cause": f"메모리 부족으로 OOMKilled 발생 (현재 limit: {current_limit}, 재시작: {restart_count}회)",
            "analysis": f"파드 {pod_details.get('name')}이 메모리 limit({current_limit})을 초과하여 OOMKilled됨. 재시작 횟수가 {restart_count}회로 지속적인 문제 발생 중.",
            "recommended_memory_limit": new_limit,
            "recommended_memory_request": new_request,
            "confidence": "medium",
            "additional_recommendations": [
                "애플리케이션의 메모리 사용 패턴 모니터링 권장",
                "메모리 누수 가능성 점검 필요"
            ]
        }
    
    prompt = f"""당신은 Kubernetes 전문가입니다. OOMKilled 이슈를 분석해주세요.

## 파드 정보
- 이름: {pod_details.get('name')}
- 네임스페이스: {pod_details.get('namespace')}
- 현재 메모리 Request: {pod_details.get('memory_request', 'Not set')}
- 현재 메모리 Limit: {pod_details.get('memory_limit', 'Not set')}
- 재시작 횟수: {restart_count}

## 이벤트
{events}

## 최근 로그
{logs[:2000]}

다음 형식으로 JSON 응답해주세요:
{{
    "root_cause": "근본 원인 설명",
    "analysis": "상세 분석 결과",
    "recommended_memory_limit": "권장 메모리 리미트 (예: 512Mi)",
    "recommended_memory_request": "권장 메모리 Request (예: 256Mi)",
    "confidence": "high/medium/low",
    "additional_recommendations": ["추가 권장사항 목록"]
}}

JSON만 출력하세요.
"""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    
    try:
        return _parse_json_response(response.text)
    except json.JSONDecodeError:
        return {
            "root_cause": "분석 실패",
            "analysis": response.text,
            "recommended_memory_limit": "512Mi",
            "recommended_memory_request": "256Mi",
            "confidence": "low",
            "additional_recommendations": []
        }


def analyze_crashloop_issue(
    pod_details: dict,
    events: list[dict],
    logs: str,
    restart_count: int
) -> dict:
    """CrashLoopBackOff 이슈 분석"""
    client = get_client()
    
    # LLM 없으면 규칙 기반 분석
    if client is None:
        return {
            "root_cause": f"컨테이너가 반복적으로 크래시 (재시작: {restart_count}회)",
            "analysis": f"파드 {pod_details.get('name')}이 CrashLoopBackOff 상태. 로그를 확인하여 애플리케이션 오류 원인 파악 필요.",
            "suggested_action": "restart",
            "confidence": "medium",
            "fix_steps": [
                "애플리케이션 로그 확인",
                "설정 파일/환경변수 점검",
                "리소스 제한 확인"
            ]
        }
    
    prompt = f"""당신은 Kubernetes 전문가입니다. CrashLoopBackOff 이슈를 분석해주세요.

## 파드 정보
- 이름: {pod_details.get('name')}
- 네임스페이스: {pod_details.get('namespace')}
- 재시작 횟수: {restart_count}

## 이벤트
{events}

## 최근 로그
{logs[:2000]}

다음 형식으로 JSON 응답해주세요:
{{
    "root_cause": "근본 원인 설명",
    "analysis": "상세 분석 결과",
    "suggested_action": "restart/config_change/code_fix/other",
    "confidence": "high/medium/low",
    "fix_steps": ["수정 단계 목록"]
}}

JSON만 출력하세요.
"""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    
    try:
        return _parse_json_response(response.text)
    except json.JSONDecodeError:
        return {
            "root_cause": "분석 실패",
            "analysis": response.text,
            "suggested_action": "restart",
            "confidence": "low",
            "fix_steps": []
        }


def generate_fix_summary(issue_type: str, fix_plan: dict, execution_result: str) -> str:
    """수정 결과 요약 생성"""
    client = get_client()
    
    prompt = f"""Kubernetes 이슈 수정 결과를 한국어로 요약해주세요.

## 이슈 타입
{issue_type}

## 수정 계획
{fix_plan}

## 실행 결과
{execution_result}

간결하고 명확하게 요약해주세요. 다음 모니터링 권장사항도 포함해주세요.
"""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text
