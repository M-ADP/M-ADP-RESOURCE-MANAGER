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

    @staticmethod
    def parse_cpu_to_millicores(cpu_str: str) -> int:
        """CPU 문자열을 밀리코어 단위로 변환합니다.
        
        지원 형식:
            - "100m" -> 100 밀리코어
            - "1" -> 1000 밀리코어 (1 코어)
            - "1.5" -> 1500 밀리코어
            - "2000m" -> 2000 밀리코어
        
        Args:
            cpu_str: CPU 문자열 (예: "100m", "1", "1.5")
        
        Returns:
            밀리코어 단위의 정수값
        """
        if not cpu_str:
            return 0
        
        cpu_str = str(cpu_str).strip()
        
        # 밀리코어 (예: "100m", "2000m")
        if cpu_str.endswith('m'):
            try:
                return int(cpu_str[:-1])
            except ValueError:
                return 0
        
        # 코어 (예: "1", "1.5", "2")
        try:
            cores = float(cpu_str)
            return int(cores * 1000)
        except ValueError:
            return 0

    @staticmethod
    def millicores_to_cores(millicores: int) -> float:
        """밀리코어를 코어로 변환합니다.
        
        Args:
            millicores: 밀리코어 값
        
        Returns:
            코어 단위의 부동소수점 값
        """
        return millicores / 1000.0

    @staticmethod
    def bytes_to_gibibytes(bytes_val: int) -> float:
        """바이트를 GiB로 변환합니다.
        
        Args:
            bytes_val: 바이트 값
        
        Returns:
            GiB 단위의 부동소수점 값
        """
        return bytes_val / (1024 ** 3)
