"""pytest 공통 설정 및 픽스처"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """비동기 이벤트 루프 정책 설정"""
    import asyncio
    return asyncio.get_event_loop_policy()


# 각 테스트 후 싱글톤 정리
@pytest.fixture(autouse=True)
def reset_singletons():
    """각 테스트 후 싱글톤 인스턴스 초기화"""
    yield
    
    # KubernetesClient 싱글톤 초기화
    try:
        import infra.kubernetes.client as client_module
        client_module._k8s_client_instance = None
    except ImportError:
        pass
