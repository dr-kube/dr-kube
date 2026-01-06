"""
로그 분석 에이전트 사용 예제
"""

import os
from .log_analysis_agent import LogAnalysisAgent

# 예제 1: 로컬 파일에서 로그 분석
def example_file_analysis():
    """로컬 파일에서 로그를 분석하는 예제"""
    agent = LogAnalysisAgent()
    
    # 로그 파일 경로
    log_file = "sample_error.log"
    
    result = agent.run(
        log_source=log_file,
        source_type="file"
    )
    
    print(f"분석 완료: {result['status']}")


# 예제 2: Kubernetes Pod에서 로그 수집 및 분석
def example_pod_analysis():
    """Kubernetes Pod에서 로그를 수집하고 분석하는 예제"""
    config = {
        "kubernetes_namespace": "default",
        "kubeconfig_path": os.getenv("KUBECONFIG_PATH"),
    }
    
    agent = LogAnalysisAgent(config=config)
    
    # Pod 이름
    pod_name = "my-app-pod-12345"
    
    result = agent.run(
        log_source=pod_name,
        source_type="pod"
    )
    
    print(f"분석 완료: {result['status']}")


# 예제 3: 라벨 셀렉터로 여러 Pod에서 로그 수집
def example_label_analysis():
    """라벨 셀렉터로 여러 Pod에서 로그를 수집하는 예제"""
    config = {
        "kubernetes_namespace": "default",
    }
    
    agent = LogAnalysisAgent(config=config)
    
    # 라벨 셀렉터
    label_selector = "app=myapp"
    
    result = agent.run(
        log_source=label_selector,
        source_type="label"
    )
    
    print(f"분석 완료: {result['status']}")


# 예제 4: 실제 Git 커밋 수행 (시뮬레이션 모드 비활성화)
def example_real_commit():
    """실제 Git 커밋을 수행하는 예제 (주의: 실제 파일이 변경됩니다)"""
    config = {
        "simulate": False,  # 시뮬레이션 모드 비활성화
        "auto_approve": True,
        "repo_path": ".",
    }
    
    agent = LogAnalysisAgent(config=config)
    
    log_file = "error.log"
    
    result = agent.run(
        log_source=log_file,
        source_type="file"
    )
    
    print(f"분석 및 커밋 완료: {result['status']}")


if __name__ == "__main__":
    # 환경 변수 확인
    if not os.getenv("GOOGLE_API_KEY"):
        print("오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다")
        print("환경 변수를 설정하거나 .env 파일을 생성하세요")
        exit(1)
    
    # 예제 실행 (원하는 예제의 주석을 해제하세요)
    # example_file_analysis()
    # example_pod_analysis()
    # example_label_analysis()
    # example_real_commit()
    
    print("예제를 실행하려면 example_usage.py 파일에서 원하는 함수의 주석을 해제하세요")

