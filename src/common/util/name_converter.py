import re

from hangul_romanize import Transliter
from hangul_romanize.rule import academic


class NameConverter:
    """Kubernetes 리소스 이름 변환 유틸리티"""

    _transliter = Transliter(academic)

    @classmethod
    def to_k8s_name(cls, name: str, prefix: str = "app-") -> str:
        """임의 문자열을 Kubernetes RFC 1123 호환 이름으로 변환

        변환 순서:
        1. 한글 → 로마자 (hangul-romanize)
        2. 대문자 → 소문자
        3. 유효하지 않은 문자 → 하이픈
        4. 연속 하이픈 → 단일 하이픈
        5. 앞뒤 하이픈 제거

        Args:
            name: 변환할 이름
            prefix: 접두사 (기본값: "app-")

        Returns:
            RFC 1123 호환 이름 (소문자, 숫자, 하이픈만 포함)
        """
        result = cls._transliter.translit(name)
        result = result.lower()
        result = re.sub(r"[^a-z0-9-]", "-", result)
        result = re.sub(r"-+", "-", result)
        result = result.strip("-")
        result = prefix + result
        return result
