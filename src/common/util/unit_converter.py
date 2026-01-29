import re


class UnitConverter:

    @staticmethod
    def parse_storage_to_bytes(storage_str: str) -> int:
        """스토리지 문자열을 바이트 단위로 변환합니다.

        지원 단위: Ki, Mi, Gi, Ti, Pi, Ei (binary), K, M, G, T, P, E (decimal)
        """
        if not storage_str:
            return 0

        # 숫자와 단위 분리
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Za-z]*)$', storage_str.strip())
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2)

        # Binary units (Ki, Mi, Gi, Ti, Pi, Ei)
        binary_units = {
            '': 1,
            'Ki': 1024,
            'Mi': 1024 ** 2,
            'Gi': 1024 ** 3,
            'Ti': 1024 ** 4,
            'Pi': 1024 ** 5,
            'Ei': 1024 ** 6,
        }

        # Decimal units (K, M, G, T, P, E)
        decimal_units = {
            'K': 1000,
            'M': 1000 ** 2,
            'G': 1000 ** 3,
            'T': 1000 ** 4,
            'P': 1000 ** 5,
            'E': 1000 ** 6,
        }

        if unit in binary_units:
            return int(value * binary_units[unit])
        elif unit in decimal_units:
            return int(value * decimal_units[unit])
        else:
            return int(value)
