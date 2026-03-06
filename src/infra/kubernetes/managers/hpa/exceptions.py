"""HPA Manager 예외 클래스"""


class HpaException(Exception):
    """HPA 관련 기본 예외"""
    pass


class HpaCreateException(HpaException):
    """HPA 생성 실패 예외"""
    pass


class HpaNotFoundException(HpaException):
    """HPA를 찾을 수 없는 경우 예외"""
    pass


class HpaUpdateException(HpaException):
    """HPA 업데이트 실패 예외"""
    pass


class HpaDeleteException(HpaException):
    """HPA 삭제 실패 예외"""
    pass
